from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.models import Analysis, Article, ArticleAuthor, Author, Cluster, ClusterEntity, Entity, Saga, Source
from noticias_api.db.session import get_session
from noticias_api.pipeline.runner import PipelineConfig, _analyze_top_clusters

router = APIRouter(tags=["clusters"])


class SourceRef(BaseModel):
    slug: str
    name: str
    editorial_group: str


class AuthorRef(BaseModel):
    name: str
    slug: str
    is_synthetic: bool


class ArticleOut(BaseModel):
    id: int
    source: SourceRef
    title: str
    url: str
    summary: str | None
    has_full_text: bool
    published_at: datetime | None
    authors: list[AuthorRef] = []


class AnalysisOut(BaseModel):
    headline: str | None
    common_facts: list[str]
    by_source: dict
    omissions: list[dict]
    divergences: list[dict]
    model: str | None
    prompt_version: str | None
    generated_at: datetime


class SagaRef(BaseModel):
    id: int
    title: str


class EntityRef(BaseModel):
    id: int
    name: str
    kind: str


class ClusterDetail(BaseModel):
    id: int
    first_seen_at: datetime
    last_seen_at: datetime
    article_count: int
    source_count: int
    analysis: AnalysisOut | None
    articles: list[ArticleOut]
    saga: SagaRef | None
    entities: list[EntityRef]
    topic: str | None


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

    # Fetch authors for all articles in this cluster in one query
    auth_rows = (await session.execute(
        select(Article.id, Author.name, Author.canonical, Author.is_synthetic, ArticleAuthor.position)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .join(Author, Author.id == ArticleAuthor.author_id)
        .where(Article.cluster_id == cluster_id)
        .order_by(ArticleAuthor.position)
    )).all()
    by_article: dict[int, list[AuthorRef]] = {}
    for art_id, name, canon, is_syn, _pos in auth_rows:
        by_article.setdefault(art_id, []).append(
            AuthorRef(name=name, slug=canon.replace(" ", "-"), is_synthetic=is_syn)
        )

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
                authors=by_article.get(art.id, []),
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

    saga_ref: SagaRef | None = None
    if cluster.saga_id:
        saga = await session.get(Saga, cluster.saga_id)
        if saga:
            saga_ref = SagaRef(id=saga.id, title=saga.title)

    ent_rows = await session.scalars(
        select(Entity)
        .join(ClusterEntity, ClusterEntity.entity_id == Entity.id)
        .where(ClusterEntity.cluster_id == cluster_id)
        .order_by(Entity.kind, Entity.name)
    )
    entities = [EntityRef(id=e.id, name=e.name, kind=e.kind) for e in ent_rows.all()]

    return ClusterDetail(
        id=cluster.id,
        first_seen_at=cluster.first_seen_at,
        last_seen_at=cluster.last_seen_at,
        article_count=cluster.article_count,
        source_count=cluster.source_count,
        analysis=analysis_out,
        articles=article_outs,
        saga=saga_ref,
        entities=entities,
        topic=cluster.topic,
    )


@router.post("/clusters/{cluster_id}/regenerate-analysis", response_model=AnalysisOut | None)
async def regenerate_analysis(
    cluster_id: int,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> AnalysisOut:
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="cluster not found")
    if cluster.article_count < 1:
        raise HTTPException(status_code=400, detail="cluster has no articles to analyze")

    # Drop existing analysis to force regeneration
    await session.execute(
        delete(Analysis).where(Analysis.cluster_id == cluster_id)
    )
    await session.commit()

    cfg = PipelineConfig(
        top_n=settings.top_n_clusters,
        similarity_threshold=settings.similarity_threshold,
        window_hours=settings.cluster_window_hours,
        embedding_model=settings.embedding_model,
        analysis_model=settings.chat_model_analysis,
        user_agent=settings.user_agent,
        max_concurrent=settings.max_concurrent_fetches,
        merge_threshold=settings.merge_threshold,
        merge_window_hours=settings.merge_window_hours,
        saga_threshold=settings.saga_threshold,
        saga_window_hours=settings.saga_window_hours,
        enable_entity_extraction=settings.enable_entity_extraction,
        entity_extraction_model=settings.entity_extraction_model,
    )
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    await _analyze_top_clusters(
        session, client, cfg, only_cluster_ids={cluster_id}
    )

    new_analysis = await session.scalar(
        select(Analysis).where(Analysis.cluster_id == cluster_id)
    )
    if new_analysis is None:
        raise HTTPException(status_code=502, detail="analysis regeneration failed")
    return AnalysisOut(
        headline=new_analysis.headline,
        common_facts=new_analysis.common_facts or [],
        by_source=new_analysis.by_source or {},
        omissions=new_analysis.omissions or [],
        divergences=new_analysis.divergences or [],
        model=new_analysis.model,
        prompt_version=new_analysis.prompt_version,
        generated_at=new_analysis.generated_at,
    )


@router.get("/clusters/{cluster_id}/by-author")
async def cluster_by_author(
    cluster_id: int,
    a: str,
    b: str,
    session: AsyncSession = Depends(get_session),
):
    from noticias_api.api.authors import _author_by_slug
    from noticias_api.db.models import Article, ArticleAuthor

    author_a = await _author_by_slug(session, a)
    author_b = await _author_by_slug(session, b)

    arts_a = (await session.scalars(
        select(Article)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(Article.cluster_id == cluster_id, ArticleAuthor.author_id == author_a.id)
    )).all()
    arts_b = (await session.scalars(
        select(Article)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(Article.cluster_id == cluster_id, ArticleAuthor.author_id == author_b.id)
    )).all()

    def shape(arts):
        return [
            {"id": x.id, "title": x.title, "url": x.url,
             "published_at": x.published_at.isoformat() if x.published_at else None}
            for x in arts
        ]
    return {
        "cluster_id": cluster_id,
        "a": {"slug": a, "name": author_a.name, "articles": shape(arts_a)},
        "b": {"slug": b, "name": author_b.name, "articles": shape(arts_b)},
    }
