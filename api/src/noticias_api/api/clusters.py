from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["clusters"])


class SourceRef(BaseModel):
    slug: str
    name: str
    editorial_group: str


class ArticleOut(BaseModel):
    id: int
    source: SourceRef
    title: str
    url: str
    summary: str | None
    has_full_text: bool
    published_at: datetime | None


class AnalysisOut(BaseModel):
    headline: str | None
    common_facts: list[str]
    by_source: dict
    omissions: list[dict]
    divergences: list[dict]
    model: str | None
    prompt_version: str | None
    generated_at: datetime


class ClusterDetail(BaseModel):
    id: int
    first_seen_at: datetime
    last_seen_at: datetime
    article_count: int
    source_count: int
    analysis: AnalysisOut | None
    articles: list[ArticleOut]


@router.get("/clusters/{cluster_id}", response_model=ClusterDetail)
async def get_cluster(
    cluster_id: int, session: AsyncSession = Depends(get_session)
) -> ClusterDetail:
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="cluster not found")

    analysis = await session.scalar(
        select(Analysis).where(Analysis.cluster_id == cluster_id)
    )
    articles = (
        await session.scalars(
            select(Article)
            .where(Article.cluster_id == cluster_id)
            .order_by(Article.published_at)
        )
    ).all()

    article_outs: list[ArticleOut] = []
    for art in articles:
        src = await session.get(Source, art.source_id)
        article_outs.append(
            ArticleOut(
                id=art.id,
                source=SourceRef(
                    slug=src.slug, name=src.name, editorial_group=src.editorial_group
                ),
                title=art.title,
                url=art.url,
                summary=art.summary,
                has_full_text=art.has_full_text,
                published_at=art.published_at,
            )
        )

    analysis_out: AnalysisOut | None = None
    if analysis:
        analysis_out = AnalysisOut(
            headline=analysis.headline,
            common_facts=analysis.common_facts or [],
            by_source=analysis.by_source or {},
            omissions=analysis.omissions or [],
            divergences=analysis.divergences or [],
            model=analysis.model,
            prompt_version=analysis.prompt_version,
            generated_at=analysis.generated_at,
        )

    return ClusterDetail(
        id=cluster.id,
        first_seen_at=cluster.first_seen_at,
        last_seen_at=cluster.last_seen_at,
        article_count=cluster.article_count,
        source_count=cluster.source_count,
        analysis=analysis_out,
        articles=article_outs,
    )
