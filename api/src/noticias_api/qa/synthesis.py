import logging
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

from noticias_api.qa.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
Sos un analista que responde preguntas sobre un corpus de noticias argentinas.
Te paso fragmentos numerados y una pregunta. Respondé en español, conciso y específico.

REGLAS:
- Citá con [N] inline cualquier afirmación específica que provenga de un fragmento. Ej: "La inflación de abril fue del 4,2% según el INDEC [3]."
- Si la respuesta no está en los fragmentos, decí explícitamente "No encontré esa información en el corpus disponible."
- No inventes datos. No uses conocimiento externo.
- Si querés contrastar fuentes, citá ambas: "La Nación enfatiza X [2], mientras que Página 12 destaca Y [5]."
- Mantené la respuesta entre 100 y 400 palabras según la complejidad.
"""


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
) -> SynthesisResult:
    user_prompt = build_user_prompt(question, chunks)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    used = parse_citations(answer)
    return SynthesisResult(answer=answer, used_citations=used)
