from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["briefings"])


class ClusterSummary(BaseModel):
    id: int
    headline: str | None
    source_count: int
    article_count: int
    sources: list[str]
    rank_score: float | None
    common_facts: list[str]
    divergence_count: int


class BriefingOut(BaseModel):
    date: date
    generated_at: datetime | None
    clusters: list[ClusterSummary]


async def _build_briefing(session: AsyncSession, target: date) -> BriefingOut:
    clusters = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.display_date == target)
            .order_by(Cluster.rank_score.desc().nullslast())
        )
    ).all()

    summaries: list[ClusterSummary] = []
    generated_at: datetime | None = None

    for c in clusters:
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == c.id)
        )
        article_sources = (
            await session.scalars(
                select(Source.slug)
                .join(Article, Article.source_id == Source.id)
                .where(Article.cluster_id == c.id)
                .distinct()
            )
        ).all()
        summaries.append(
            ClusterSummary(
                id=c.id,
                headline=analysis.headline if analysis else None,
                source_count=c.source_count,
                article_count=c.article_count,
                sources=list(article_sources),
                rank_score=c.rank_score,
                common_facts=analysis.common_facts if analysis else [],
                divergence_count=len(analysis.divergences) if analysis else 0,
            )
        )
        if analysis and (generated_at is None or analysis.generated_at > generated_at):
            generated_at = analysis.generated_at

    return BriefingOut(date=target, generated_at=generated_at, clusters=summaries)


@router.get("/briefings/today", response_model=BriefingOut)
async def get_today(session: AsyncSession = Depends(get_session)) -> BriefingOut:
    return await _build_briefing(session, date.today())


@router.get("/briefings", response_model=list[date])
async def list_dates(session: AsyncSession = Depends(get_session)) -> list[date]:
    rows = await session.scalars(
        select(distinct(Cluster.display_date))
        .where(Cluster.display_date.is_not(None))
        .order_by(Cluster.display_date.desc())
    )
    return [d for d in rows.all() if d is not None]


@router.get("/briefings/{target_date}", response_model=BriefingOut)
async def get_by_date(
    target_date: date, session: AsyncSession = Depends(get_session)
) -> BriefingOut:
    return await _build_briefing(session, target_date)
