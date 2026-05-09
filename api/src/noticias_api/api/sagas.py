from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Cluster, Saga
from noticias_api.db.session import get_session

router = APIRouter(tags=["sagas"])


class SagaSummary(BaseModel):
    id: int
    title: str
    cluster_count: int
    source_count: int
    article_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class SagaClusterRef(BaseModel):
    id: int
    headline: str | None
    source_count: int
    article_count: int
    last_seen_at: datetime
    is_top: bool


class SagaDetail(SagaSummary):
    clusters: list[SagaClusterRef]


@router.get("/sagas", response_model=list[SagaSummary])
async def list_sagas(limit: int = 30, session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(Saga).order_by(Saga.last_seen_at.desc()).limit(limit)
    )
    return list(rows.all())


@router.get("/sagas/{saga_id}", response_model=SagaDetail)
async def get_saga(saga_id: int, session: AsyncSession = Depends(get_session)):
    saga = await session.get(Saga, saga_id)
    if not saga:
        raise HTTPException(404, "saga not found")
    clusters = (await session.scalars(
        select(Cluster).where(Cluster.saga_id == saga_id)
        .order_by(Cluster.last_seen_at.desc())
    )).all()
    refs: list[SagaClusterRef] = []
    for c in clusters:
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == c.id)
        )
        refs.append(SagaClusterRef(
            id=c.id,
            headline=analysis.headline if analysis else None,
            source_count=c.source_count,
            article_count=c.article_count,
            last_seen_at=c.last_seen_at,
            is_top=c.is_top,
        ))
    return SagaDetail(
        id=saga.id, title=saga.title,
        cluster_count=saga.cluster_count, source_count=saga.source_count,
        article_count=saga.article_count,
        first_seen_at=saga.first_seen_at, last_seen_at=saga.last_seen_at,
        clusters=refs,
    )
