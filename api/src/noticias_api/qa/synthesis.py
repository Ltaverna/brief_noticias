import logging
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

from noticias_api.qa.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


# Legacy constant kept for backwards compatibility with existing tests.
SYSTEM_PROMPT = """\
Sos un analista que responde preguntas sobre un corpus de noticias argentinas.
Te paso fragmentos numerados y una pregunta. Respondé en español, conciso y específico.

REGLAS:
- Citá con [N] inline cualquier afirmación específica que provenga de un fragmento. Ej: "La inflación de abril fue del 4,2% según el INDEC [3]."
- Si la respuesta no está en los fragmentos, decí explícitamente "No encontré esa información en el corpus disponible."
- No inventes datos. No uses conocimiento externo.
- Si querés contrastar fuentes, citá ambas: "La Nación enfatiza X [2], mientras que Página 12 destaca Y [5]."
- Mantené la respuesta entre 100 y 400 palabras según la complejidad.
- Si esta es una pregunta de seguimiento (hay turnos previos en el historial), tené en cuenta el contexto de la conversación.
"""

SYSTEM_PROMPTS: dict[str, str] = {
    "confident": """\
Sos un analista que responde preguntas sobre un corpus de noticias argentinas.
Te paso fragmentos numerados y una pregunta. Respondé en español, conciso y específico.

REGLAS:
- Citá con [N] inline cualquier afirmación específica que provenga de un fragmento. Ej: "La inflación de abril fue del 4,2% según el INDEC [3]."
- Si la respuesta no está en los fragmentos, decí explícitamente "No encontré esa información en el corpus disponible."
- No inventes datos. No uses conocimiento externo.
- Si querés contrastar fuentes, citá ambas: "La Nación enfatiza X [2], mientras que Página 12 destaca Y [5]."
- Mantené la respuesta entre 100 y 400 palabras según la complejidad.
- Si esta es una pregunta de seguimiento (hay turnos previos en el historial), tené en cuenta el contexto de la conversación.
""",
    "partial": """\
Sos un analista que responde preguntas sobre un corpus de noticias argentinas.
Te paso fragmentos numerados y una pregunta. La cobertura disponible es PARCIAL —
algunos fragmentos solo tocan el tema tangencialmente.

REGLAS:
- Citá con [N] inline cualquier afirmación específica.
- Sé EXPLÍCITO sobre la limitación: empezá la respuesta con algo como
  "La cobertura es limitada, pero..." o "Solo encontré información parcial sobre esto".
- No completes con conocimiento externo. Si los fragmentos no cubren un aspecto,
  decí que no hay datos en el corpus.
- Mantené la respuesta entre 80 y 300 palabras.
- Si esta es una pregunta de seguimiento, tené en cuenta el contexto.
""",
}


CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class SynthesisResult:
    answer: str
    used_citations: list[int]  # numbers actually mentioned in the answer


def build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    parts = [f"Pregunta: {question}\n", "Fragmentos:"]
    for i, c in enumerate(chunks, start=1):
        date_str = c.published_at.strftime("%Y-%m-%d") if c.published_at else "s/f"
        parts.append(
            f"\n[{i}] ({c.source_slug}, {date_str}): {c.text}"
        )
    return "\n".join(parts)


def parse_citations(answer: str) -> list[int]:
    """Return ordered, deduped list of [N] markers found in the answer."""
    seen: list[int] = []
    for m in CITATION_RE.finditer(answer):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


async def synthesize(
    client: AsyncOpenAI,
    *,
    question: str,
    chunks: list[RetrievedChunk],
    model: str,
    history: list[dict] | None = None,  # list of {role, content} prior turns
    confidence_hint: str = "confident",
) -> SynthesisResult:
    """Generate an answer grounded in the retrieved chunks.

    `history` is a list of prior conversation turns (dicts with `role` and
    `content` keys) that are injected between the system prompt and the current
    user message to provide multi-turn context.

    `confidence_hint` selects which system prompt to use:
    - "confident": full coverage — standard analytical prompt.
    - "partial": limited coverage — prompt warns model to flag gaps explicitly.
    Any unknown value falls back to "confident".
    """
    user_prompt = build_user_prompt(question, chunks)
    system_prompt = SYSTEM_PROMPTS.get(confidence_hint, SYSTEM_PROMPTS["confident"])
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for turn in (history or []):
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    used = parse_citations(answer)
    return SynthesisResult(answer=answer, used_citations=used)
