from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["search"])


class ArticleHit(BaseModel):
    id: int
    title: str
    url: str
    source_slug: str
    cluster_id: int | None
    published_at: str | None
    rank: float


class ClusterHit(BaseModel):
    id: int
    headline: str | None
    source_count: int
    article_count: int
    rank: float


class SearchResults(BaseModel):
    query: str
    clusters: list[ClusterHit]
    articles: list[ArticleHit]


@router.get("/search", response_model=SearchResults)
async def search(
    q: Annotated[str, Query(min_length=2, max_length=200)],
    limit: int = 30,
    session: AsyncSession = Depends(get_session),
) -> SearchResults:
    tsq = func.plainto_tsquery("spanish", q)

    # Cluster hits via Analysis FTS
    cluster_rows = await session.execute(
        select(
            Cluster.id,
            Cluster.source_count,
            Cluster.article_count,
            Analysis.headline,
            func.ts_rank(Analysis.tsv, tsq).label("rank"),
        )
        .join(Analysis, Analysis.cluster_id == Cluster.id)
        .where(Analysis.tsv.op("@@")(tsq))
        .order_by(desc("rank"))
        .limit(limit)
    )
    clusters = [
        ClusterHit(
            id=r.id,
            headline=r.headline,
            source_count=r.source_count,
            article_count=r.article_count,
            rank=float(r.rank or 0.0),
        )
        for r in cluster_rows.all()
    ]

    # Article hits
    article_rows = await session.execute(
        select(
            Article.id,
            Article.title,
            Article.url,
            Article.published_at,
            Article.cluster_id,
            Source.slug,
            func.ts_rank(Article.tsv, tsq).label("rank"),
        )
        .join(Source, Source.id == Article.source_id)
        .where(Article.tsv.op("@@")(tsq))
        .order_by(desc("rank"))
        .limit(limit)
    )
    articles = [
        ArticleHit(
            id=r.id,
            title=r.title,
            url=r.url,
            source_slug=r.slug,
            cluster_id=r.cluster_id,
            published_at=r.published_at.isoformat() if r.published_at else None,
            rank=float(r.rank or 0.0),
        )
        for r in article_rows.all()
    ]

    return SearchResults(query=q, clusters=clusters, articles=articles)
