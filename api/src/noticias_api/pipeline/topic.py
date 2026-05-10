import json
import logging
from typing import Final

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

TOPICS: Final[tuple[str, ...]] = (
    "politica",
    "economia",
    "deportes",
    "internacional",
    "sociedad",
    "espectaculos",
    "otros",
)

SYSTEM_PROMPT = """\
Clasificá el tema principal de una historia de noticias argentinas. Devolvé JSON:

{"topic": "politica|economia|deportes|internacional|sociedad|espectaculos|otros"}

Reglas:
- "politica": gobierno argentino, elecciones, partidos, Congreso, Justicia local con derivaciones políticas.
- "economia": inflación, dólar, mercados, empresas, tarifas, jubilaciones, finanzas, comercio.
- "deportes": fútbol, tenis, automovilismo, cualquier deporte.
- "internacional": noticias del exterior, política internacional, conflictos foráneos.
- "sociedad": clima, accidentes, salud, educación, sucesos, cultura general.
- "espectaculos": música, cine, TV, celebridades, farándula.
- "otros": cualquier cosa que no entre claramente en las anteriores.

Solo devolvé el JSON con un único campo "topic". No expliques.
"""


class _TopicResult(BaseModel):
    topic: str = Field(min_length=3, max_length=32)


async def classify_topic(
    client: AsyncOpenAI,
    *,
    headline: str,
    common_facts: list[str],
    model: str,
) -> str | None:
    """Return one of TOPICS, or None on parse failure."""
    if not headline:
        return None
    body = headline + "\n\n" + "\n".join(f"- {f}" for f in (common_facts or []))[:2000]
    for attempt, temp in enumerate([0.0, 0.0]):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": body},
                ],
                response_format={"type": "json_object"},
                temperature=temp,
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            parsed = _TopicResult.model_validate(data)
            t = parsed.topic.strip().lower()
            return t if t in TOPICS else "otros"
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "classify_topic attempt %s failed: %s", attempt + 1, exc
            )
    return None


async def classify_for_top_clusters(
    session,  # AsyncSession
    client: AsyncOpenAI,
    *,
    model: str,
) -> dict[str, int]:
    """Classify all is_top clusters that lack a topic. Idempotent."""
    from sqlalchemy import select, update
    from noticias_api.db.models import Analysis, Cluster

    rows = (
        await session.execute(
            select(Cluster, Analysis)
            .join(Analysis, Analysis.cluster_id == Cluster.id)
            .where(Cluster.is_top.is_(True))
            .where(Cluster.topic.is_(None))
        )
    ).all()

    classified = 0
    for cluster, analysis in rows:
        if not analysis.headline:
            continue
        topic = await classify_topic(
            client,
            headline=analysis.headline,
            common_facts=list(analysis.common_facts or []),
            model=model,
        )
        if topic is None:
            continue
        await session.execute(
            update(Cluster).where(Cluster.id == cluster.id).values(topic=topic)
        )
        classified += 1
    await session.commit()
    return {"classified": classified}
