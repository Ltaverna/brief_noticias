"""LLM-driven author profile (M3)."""
import json

from openai import AsyncOpenAI
from pydantic import BaseModel

SYSTEM_PROMPT = """\
Analizás patrones editoriales de un periodista a partir de los análisis comparativos
de sus notas. Devolvé JSON con esta estructura exacta:

{
  "framings_recurrentes": ["..."],
  "fuentes_citadas_frecuentes": ["..."],
  "entidades_dominantes": ["..."],
  "tono_caracteristico": "string corto",
  "temas_evitados": ["..."]
}

Reglas:
- Si la muestra es chica (n<10), prefijá cada afirmación con "Patrón sugerido:" y
  marcalo como no confirmado.
- No inventes. Si no hay evidencia para un campo, devolvé lista vacía o string vacío.
- Sé específico: en lugar de "tono crítico" decí "tono crítico hacia el gobierno
  nacional, neutral hacia provinciales".
"""


class ProfileOutput(BaseModel):
    framings_recurrentes: list[str] = []
    fuentes_citadas_frecuentes: list[str] = []
    entidades_dominantes: list[str] = []
    tono_caracteristico: str = ""
    temas_evitados: list[str] = []


async def generate_profile(
    client: AsyncOpenAI, *, model: str, samples: list[dict], n_sample: int
) -> ProfileOutput:
    """samples: list of {headline, framing} dicts from recent analyses."""
    sample_block = "\n\n".join(
        f"- {s.get('headline', '')}\n  encuadre: {s.get('framing', '')}"
        for s in samples
    )
    user = f"Muestra de {n_sample} notas del autor:\n\n{sample_block}"

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content or "{}"
    return ProfileOutput.model_validate(json.loads(raw))
