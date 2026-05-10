import json
import logging
from dataclasses import dataclass
from typing import Final, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from noticias_api.qa.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


Verdict = Literal["relevant", "ambiguous", "irrelevant"]
Confidence = Literal["confident", "partial", "empty"]


SYSTEM_PROMPT = """\
Sos un evaluador de relevancia. Te paso una pregunta y N fragmentos numerados.
Para cada fragmento, decidí si responde la pregunta:
- "relevant": el fragmento contiene información directa y útil para responder.
- "ambiguous": el fragmento toca el tema pero la conexión no es clara.
- "irrelevant": el fragmento no responde la pregunta, aunque mencione palabras similares.

Sé estricto. Si la pregunta es sobre la cobertura de un diario específico, un
fragmento de OTRO diario es "irrelevant" salvo que aporte contraste útil.

Devolvé JSON con la forma:
{ "verdicts": [{"n": 1, "verdict": "relevant"}, {"n": 2, "verdict": "irrelevant"}, ...] }

Solo JSON. No expliques.
"""


class _Verdict(BaseModel):
    n: int
    verdict: str


class _VerdictsList(BaseModel):
    verdicts: list[_Verdict]


@dataclass
class CragResult:
    verdicts: dict[int, Verdict]      # n -> verdict (1-based)
    confidence: Confidence
    relevant_indices: list[int]       # 1-based indices of chunks judged relevant
    ambiguous_indices: list[int]


SNIPPET_LEN: Final = 600


def _build_user_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    parts = [f"Pregunta: {query}", "", "Fragmentos:"]
    for i, c in enumerate(chunks, start=1):
        # Use a snippet, not full body, to keep this judging call cheap.
        body = c.text[:SNIPPET_LEN]
        parts.append(f"\n[{i}] ({c.source_slug}): {body}")
    return "\n".join(parts)


def _decide_confidence(
    verdicts: dict[int, Verdict], min_relevant: int
) -> Confidence:
    relevant_count = sum(1 for v in verdicts.values() if v == "relevant")
    if relevant_count >= min_relevant:
        return "confident"
    if relevant_count >= 1:
        return "partial"
    return "empty"


async def evaluate_relevance(
    client: AsyncOpenAI,
    *,
    query: str,
    chunks: list[RetrievedChunk],
    model: str,
    min_relevant: int = 3,
) -> CragResult:
    """Evaluate per-chunk relevance with an LLM and return a CragResult.

    Returns confidence="empty" immediately when chunks is empty.
    On parse failure, falls back to treating all chunks as "ambiguous" with
    confidence="partial" so synthesis can still proceed cautiously.
    """
    if not chunks:
        return CragResult(
            verdicts={}, confidence="empty",
            relevant_indices=[], ambiguous_indices=[],
        )

    user_prompt = _build_user_prompt(query, chunks)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        parsed = _VerdictsList.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        # On parse failure, treat all as ambiguous (don't block) — partial confidence
        logger.warning("crag parse failed: %s; defaulting to all-ambiguous", exc)
        verdicts: dict[int, Verdict] = {i: "ambiguous" for i in range(1, len(chunks) + 1)}
        return CragResult(
            verdicts=verdicts, confidence="partial",
            relevant_indices=[], ambiguous_indices=list(range(1, len(chunks) + 1)),
        )

    # Normalize unknown verdicts to "ambiguous"
    verdicts: dict[int, Verdict] = {}
    for v in parsed.verdicts:
        if not (1 <= v.n <= len(chunks)):
            continue
        verdict_str = v.verdict.strip().lower()
        if verdict_str not in ("relevant", "ambiguous", "irrelevant"):
            verdict_str = "ambiguous"
        verdicts[v.n] = verdict_str  # type: ignore[assignment]

    # Any chunk the LLM didn't return is treated as ambiguous (defensive)
    for n in range(1, len(chunks) + 1):
        verdicts.setdefault(n, "ambiguous")

    relevant_indices = sorted(n for n, v in verdicts.items() if v == "relevant")
    ambiguous_indices = sorted(n for n, v in verdicts.items() if v == "ambiguous")
    confidence = _decide_confidence(verdicts, min_relevant)

    return CragResult(
        verdicts=verdicts,
        confidence=confidence,
        relevant_indices=relevant_indices,
        ambiguous_indices=ambiguous_indices,
    )


def filter_chunks(
    chunks: list[RetrievedChunk], result: CragResult,
) -> list[RetrievedChunk]:
    """Apply the CRAG decision: drop irrelevant chunks.

    - confident: keep relevant + ambiguous (drop irrelevant).
    - partial: keep relevant + top-3 ambiguous.
    - empty: return [] (caller must short-circuit).
    """
    if result.confidence == "empty":
        return []

    keep_set = set(result.relevant_indices)
    if result.confidence == "partial":
        # Add up to 3 ambiguous to give the synthesizer some material
        keep_set.update(result.ambiguous_indices[:3])
    elif result.confidence == "confident":
        # Confident: keep relevant + all ambiguous; drop only irrelevant
        keep_set.update(result.ambiguous_indices)

    out: list[RetrievedChunk] = []
    for i, c in enumerate(chunks, start=1):
        if i in keep_set:
            out.append(c)
    return out


EMPTY_ANSWER: Final = (
    "No encontré información sobre esto en el corpus disponible. "
    "Probá ampliar la pregunta o consultá si el tema fue cubierto en otras fechas."
)
