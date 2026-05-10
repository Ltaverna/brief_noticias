import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Cluster, ClusterEntity, Entity

logger = logging.getLogger(__name__)

ENTITY_KINDS = ("person", "org", "place", "event")

ENTITY_SYSTEM_PROMPT = """\
Extraé entidades nombradas (named entities) del texto. Devolvé JSON con arrays de strings:

{
  "persons": ["nombres completos de personas, ej: 'Manuel Adorni' no 'Adorni'"],
  "orgs": ["organizaciones, partidos, instituciones, empresas"],
  "places": ["ciudades, países, lugares específicos"],
  "events": ["eventos nombrados, ej: 'Adornigate', 'Mundial 2026', 'Caso YPF'"]
}

Reglas:
- Usá nombre completo cuando lo conozcas (Manuel Adorni, no Adorni; Patricia Bullrich, no Bullrich).
- No repitas la misma entidad.
- Solo entidades realmente mencionadas en el texto (no inventes).
- Si una entidad puede caer en dos categorías, elegí la más específica (Casa Rosada → place).
- No incluyas pronombres ni roles genéricos (ej: 'el presidente' sin nombre).

Devolvé únicamente JSON válido.
"""


class EntityExtractionResult(BaseModel):
    persons: list[str] = []
    orgs: list[str] = []
    places: list[str] = []
    events: list[str] = []

    def to_records(self) -> list[tuple[str, str]]:
        """Yield (kind, name) pairs."""
        out: list[tuple[str, str]] = []
        for name in self.persons:
            out.append(("person", name.strip()))
        for name in self.orgs:
            out.append(("org", name.strip()))
        for name in self.places:
            out.append(("place", name.strip()))
        for name in self.events:
            out.append(("event", name.strip()))
        return [(k, n) for k, n in out if n]


_CANON_RE = re.compile(r"[^\w\s]", re.UNICODE)


def canonicalize(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = _CANON_RE.sub(" ", name.lower())
    return " ".join(s.split())


async def extract_entities(
    client: AsyncOpenAI, *, headline: str, common_facts: list[str], model: str
) -> EntityExtractionResult | None:
    """Call the LLM to extract entities. Returns None if parsing failed twice."""
    body = headline + "\n\n" + "\n".join(f"- {f}" for f in (common_facts or []))
    for attempt, temp in enumerate([0.1, 0.0]):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": ENTITY_SYSTEM_PROMPT},
                    {"role": "user", "content": body},
                ],
                response_format={"type": "json_object"},
                temperature=temp,
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            return EntityExtractionResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "extract_entities attempt %s failed: %s", attempt + 1, exc
            )
    return None


async def persist_entities(
    session: AsyncSession,
    cluster_id: int,
    extraction: EntityExtractionResult,
) -> int:
    """Upsert entities; (re)create cluster_entities rows. Returns count of associations."""
    records = extraction.to_records()
    if not records:
        return 0

    # Reset previous links for this cluster (re-extraction is authoritative)
    from sqlalchemy import delete as _delete
    await session.execute(
        _delete(ClusterEntity).where(ClusterEntity.cluster_id == cluster_id)
    )

    seen: set[tuple[str, str]] = set()
    associations = 0
    now = datetime.now(UTC)

    for kind, name in records:
        canon = canonicalize(name)
        if not canon:
            continue
        key = (canon, kind)
        if key in seen:
            continue
        seen.add(key)

        # Upsert entity
        existing = await session.scalar(
            select(Entity).where(Entity.canonical == canon, Entity.kind == kind)
        )
        if existing:
            ent = existing
            ent.last_seen_at = now
            ent.mention_count = (ent.mention_count or 0) + 1
            # Prefer the longer/fuller name as canonical display name
            if len(name) > len(ent.name):
                ent.name = name
        else:
            ent = Entity(
                name=name, kind=kind, canonical=canon,
                last_seen_at=now, mention_count=1,
            )
            session.add(ent)
            await session.flush()

        session.add(
            ClusterEntity(cluster_id=cluster_id, entity_id=ent.id, mention_count=1)
        )
        associations += 1

    await session.commit()
    return associations


async def extract_for_top_clusters(
    session: AsyncSession,
    client: AsyncOpenAI,
    *,
    model: str,
) -> dict[str, int]:
    """For each is_top cluster with an analysis, extract entities and persist.

    Idempotent: a cluster whose entities were already extracted (cluster_entities
    rows exist) is skipped, unless the analysis was regenerated more recently.
    """
    rows = (
        await session.execute(
            select(Cluster, Analysis)
            .join(Analysis, Analysis.cluster_id == Cluster.id)
            .where(Cluster.is_top.is_(True))
        )
    ).all()

    extracted = 0
    skipped = 0
    for cluster, analysis in rows:
        # Skip if we already have associations newer than the analysis
        existing_link = await session.scalar(
            select(func.count())
            .select_from(ClusterEntity)
            .where(ClusterEntity.cluster_id == cluster.id)
        )
        if existing_link:
            skipped += 1
            continue

        if not analysis.headline:
            continue

        result = await extract_entities(
            client,
            headline=analysis.headline,
            common_facts=list(analysis.common_facts or []),
            model=model,
        )
        if result is None:
            continue
        await persist_entities(session, cluster.id, result)
        extracted += 1

    return {"clusters_extracted": extracted, "clusters_skipped": skipped}
