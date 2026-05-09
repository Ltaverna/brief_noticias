import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import (
    Analysis,
    Cluster,
    ClusterEntity,
    Entity,
)
from noticias_api.db.session import get_session

router = APIRouter(tags=["analytics"])


TONES = ["favorable", "celebratorio", "neutral", "critico", "esceptico", "alarmista", "otro"]


def normalize_tone(raw: str | None) -> str:
    if not raw:
        return "otro"
    s = raw.strip().lower()
    s = "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )
    return s if s in TONES else "otro"


def week_key(d: datetime) -> str:
    """ISO week start (Monday) as YYYY-MM-DD."""
    monday = d.date() - timedelta(days=d.weekday())
    return monday.isoformat()


def day_key(d: datetime) -> str:
    return d.date().isoformat()


class ToneTrends(BaseModel):
    buckets: list[str]
    sources: list[str]
    tones: list[str]
    data: dict[str, dict[str, dict[str, int]]]  # source -> bucket -> tone -> count


@router.get("/analytics/tone-trends", response_model=ToneTrends)
async def tone_trends(
    entity: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    since: date | None = None,
    until: date | None = None,
    bucket: Annotated[str, Query(pattern="^(week|day)$")] = "week",
    session: AsyncSession = Depends(get_session),
):
    until = until or date.today()
    since = since or (until - timedelta(days=30))

    stmt = (
        select(Analysis, Cluster.last_seen_at)
        .join(Cluster, Cluster.id == Analysis.cluster_id)
        .where(Cluster.last_seen_at >= since)
        .where(Cluster.last_seen_at <= datetime.combine(until, datetime.max.time()))
    )
    if entity:
        stmt = (
            stmt.join(ClusterEntity, ClusterEntity.cluster_id == Cluster.id)
            .join(Entity, Entity.id == ClusterEntity.entity_id)
            .where(Entity.canonical == entity.lower().strip())
        )

    rows = (await session.execute(stmt)).all()

    keyfn = week_key if bucket == "week" else day_key
    counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    sources_seen: set[str] = set()
    buckets_seen: set[str] = set()

    for analysis, ts in rows:
        if ts is None:
            continue
        bk = keyfn(ts if isinstance(ts, datetime) else datetime.combine(ts, datetime.min.time()))
        buckets_seen.add(bk)
        for slug, info in (analysis.by_source or {}).items():
            tone = normalize_tone(info.get("tone") if isinstance(info, dict) else None)
            counts[slug][bk][tone] += 1
            sources_seen.add(slug)

    return ToneTrends(
        buckets=sorted(buckets_seen),
        sources=sorted(sources_seen),
        tones=TONES,
        data={
            s: {b: dict(counts[s][b]) for b in counts[s]}
            for s in counts
        },
    )


class CellTone(BaseModel):
    favorable: int
    critico: int
    neutral: int
    other: int  # everything else (celebratorio, alarmista, esceptico, otro)
    total: int


class BiasRow(BaseModel):
    source: str
    cells: dict[str, CellTone]  # entity_canonical -> CellTone


class BiasScorecard(BaseModel):
    entities: list[dict]  # [{canonical, name, cluster_count}]
    rows: list[BiasRow]


@router.get("/analytics/bias-scorecard", response_model=BiasScorecard)
async def bias_scorecard(
    since: date | None = None,
    top_entities: Annotated[int, Query(ge=2, le=20)] = 8,
    kind: Annotated[str, Query(pattern="^(person|org|place|event)$")] = "person",
    session: AsyncSession = Depends(get_session),
):
    until = date.today()
    since = since or (until - timedelta(days=30))

    # Pick top entities by cluster_count in window
    top = (
        await session.execute(
            select(
                Entity.canonical,
                Entity.name,
                func.count(ClusterEntity.cluster_id).label("ccount"),
            )
            .join(ClusterEntity, ClusterEntity.entity_id == Entity.id)
            .join(Cluster, Cluster.id == ClusterEntity.cluster_id)
            .where(Entity.kind == kind)
            .where(Cluster.last_seen_at >= since)
            .group_by(Entity.canonical, Entity.name)
            .order_by(func.count(ClusterEntity.cluster_id).desc())
            .limit(top_entities)
        )
    ).all()

    if not top:
        return BiasScorecard(entities=[], rows=[])

    canonicals = [t.canonical for t in top]
    entity_meta = [
        {"canonical": t.canonical, "name": t.name, "cluster_count": int(t.ccount)}
        for t in top
    ]

    # Pull analyses joined with cluster_entities for those entities
    stmt = (
        select(Analysis, Entity.canonical)
        .join(Cluster, Cluster.id == Analysis.cluster_id)
        .join(ClusterEntity, ClusterEntity.cluster_id == Cluster.id)
        .join(Entity, Entity.id == ClusterEntity.entity_id)
        .where(Entity.canonical.in_(canonicals))
        .where(Cluster.last_seen_at >= since)
    )
    rows = (await session.execute(stmt)).all()

    # source -> entity_canonical -> CellTone counts
    agg: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    sources_seen: set[str] = set()
    for analysis, ecanon in rows:
        for slug, info in (analysis.by_source or {}).items():
            tone = normalize_tone(info.get("tone") if isinstance(info, dict) else None)
            bucket = (
                "favorable" if tone in ("favorable", "celebratorio")
                else "critico" if tone in ("critico", "esceptico")
                else "neutral" if tone == "neutral"
                else "other"
            )
            agg[slug][ecanon][bucket] += 1
            agg[slug][ecanon]["total"] += 1
            sources_seen.add(slug)

    bias_rows: list[BiasRow] = []
    for s in sorted(sources_seen):
        cells: dict[str, CellTone] = {}
        for ec in canonicals:
            counts = agg[s].get(ec) or {}
            cells[ec] = CellTone(
                favorable=counts.get("favorable", 0),
                critico=counts.get("critico", 0),
                neutral=counts.get("neutral", 0),
                other=counts.get("other", 0),
                total=counts.get("total", 0),
            )
        bias_rows.append(BiasRow(source=s, cells=cells))

    return BiasScorecard(entities=entity_meta, rows=bias_rows)
