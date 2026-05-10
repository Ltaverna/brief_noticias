import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

HYDE_SYSTEM = """\
Generá una respuesta hipotética muy breve (2-3 oraciones) a la pregunta del usuario,
escrita como si fuera el lead de un artículo periodístico argentino.

No agregues introducción ni meta-comentarios. NO digas que no sabés. NO uses
disclaimers tipo "según fuentes". Escribí como si supieras la respuesta y
estuvieras dándola directamente. La idea es que tu salida tenga vocabulario y
forma similar a un artículo real, para usarla como query de búsqueda.

Pregunta:
"""


async def generate_hypothetical(
    client: AsyncOpenAI, *, query: str, model: str
) -> str:
    """Generate a hypothetical answer for the query to use as a retrieval embedding (HyDE).

    Falls back to the raw query if the response is empty.
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": HYDE_SYSTEM},
            {"role": "user", "content": query},
        ],
        temperature=0.4,
        max_tokens=200,
    )
    text = (response.choices[0].message.content or "").strip()
    return text if text else query
