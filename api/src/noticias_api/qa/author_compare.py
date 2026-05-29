import json

from openai import AsyncOpenAI
from pydantic import BaseModel

SYSTEM_PROMPT = """\
Compará dos periodistas a partir de sus estadísticas y perfiles. Devolvé JSON:

{
  "sintesis": "1-2 oraciones explícitas",
  "coincidencias": ["..."],
  "diferencias": ["..."],
  "tono_a": float, "tono_b": float,
  "delta_tono_significativo": boolean
}

Reglas:
- Si las muestras son chicas (<10), marcá explícitamente "evidencia limitada".
- No inventes coincidencias o diferencias sin sustento en los inputs.
- Sé concreto: cita números cuando los tengas.
"""


class CompareOutput(BaseModel):
    sintesis: str = ""
    coincidencias: list[str] = []
    diferencias: list[str] = []
    tono_a: float = 0.0
    tono_b: float = 0.0
    delta_tono_significativo: bool = False


async def compare_authors(
    client: AsyncOpenAI, *, model: str, payload: dict
) -> CompareOutput:
    user = json.dumps(payload, ensure_ascii=False, indent=2)
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
    return CompareOutput.model_validate(json.loads(raw))
