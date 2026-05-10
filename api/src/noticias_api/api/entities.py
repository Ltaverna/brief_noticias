from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(tags=["entities"])


class EntitySummary(BaseModel):
    id: int
    name: str
    kind: str
    canonical: str
    mention_count: int
    cluster_count: int
    last_seen_at: datetime


class EntityClusterRef(BaseModel):
    id: int
    headline: str | None
    source_count: int
    article_count: int
    last_seen_at: datetime
    is_top: bool


class EntityDetail(EntitySummary):
    clusters: list[EntityClusterRef]


@router.get("/entities", response_model=list[EntitySummary])
async def list_entities(
    kind: Annotated[str | None, Query(pattern="^(person|org|place|event)$")] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    session: AsyncSession = Depends(get_session),
):
    cluster_count_subq = (
        select(
            ClusterEntity.entity_id,
            func.count(ClusterEntity.cluster_id).label("cnt"),
        )
        .group_by(ClusterEntity.entity_id)
        .subquery()
    )

    stmt = (
        select(Entity, func.coalesce(cluster_count_subq.c.cnt, 0).label("cluster_count"))
        .outerjoin(cluster_count_subq, cluster_count_subq.c.entity_id == Entity.id)
        .order_by(func.coalesce(cluster_count_subq.c.cnt, 0).desc(),
                  Entity.last_seen_at.desc())
        .limit(limit)
    )
    if kind:
        stmt = stmt.where(Entity.kind == kind)
    if q:
        stmt = stmt.where(Entity.canonical.ilike(f"%{q.lower()}%"))

    rows = (await session.execute(stmt)).all()
    out: list[EntitySummary] = []
    for ent, count in rows:
        out.append(EntitySummary(
            id=ent.id, name=ent.name, kind=ent.kind, canonical=ent.canonical,
            mention_count=ent.mention_count, cluster_count=int(count),
            last_seen_at=ent.last_seen_at,
        ))
    return out


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def get_entity(entity_id: int, session: AsyncSession = Depends(get_session)):
    ent = await session.get(Entity, entity_id)
    if not ent:
        raise HTTPException(404, "entity not found")

    cluster_rows = (
        await session.execute(
            select(Cluster, Analysis.headline)
            .join(ClusterEntity, ClusterEntity.cluster_id == Cluster.id)
            .outerjoin(Analysis, Analysis.cluster_id == Cluster.id)
            .where(ClusterEntity.entity_id == entity_id)
            .order_by(Cluster.last_seen_at.desc())
            .limit(50)
        )
    ).all()

    cluster_count = len(cluster_rows)
    refs = [
        EntityClusterRef(
            id=c.id, headline=h,
            source_count=c.source_count, article_count=c.article_count,
            last_seen_at=c.last_seen_at, is_top=c.is_top,
        )
        for c, h in cluster_rows
    ]
    return EntityDetail(
        id=ent.id, name=ent.name, kind=ent.kind, canonical=ent.canonical,
        mention_count=ent.mention_count, cluster_count=cluster_count,
        last_seen_at=ent.last_seen_at, clusters=refs,
    )
