import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Run, Source
from noticias_api.pipeline.analyze import analyze_cluster, prompt_version
from noticias_api.pipeline.cluster import cluster_recent_articles
from noticias_api.pipeline.embed import build_embedding_input, embed_texts
from noticias_api.pipeline.extract import extract_content
from noticias_api.pipeline.fetch import fetch_feed, parse_feed
from noticias_api.pipeline.persist import persist_items
from noticias_api.pipeline.rank import rank_top_clusters

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    top_n: int
    similarity_threshold: float
    window_hours: int
    embedding_model: str
    analysis_model: str
    user_agent: str
    max_concurrent: int = 8


@dataclass
class RunStats:
    fetched: int = 0
    persisted: int = 0
    extracted: int = 0
    embedded: int = 0
    clustered: int = 0
    new_clusters: int = 0
    analyzed: int = 0
    errors_per_source: dict[str, int] = field(default_factory=dict)

    def dump(self) -> dict:
        return {
            "fetched": self.fetched,
            "persisted": self.persisted,
            "extracted": self.extracted,
            "embedded": self.embedded,
            "clustered": self.clustered,
            "new_clusters": self.new_clusters,
            "analyzed": self.analyzed,
            "errors_per_source": self.errors_per_source,
        }


async def run_pipeline(
    session: AsyncSession,
    cfg: PipelineConfig,
    *,
    trigger: str,
    openai_client: AsyncOpenAI | None = None,
) -> int:
    run = Run(trigger=trigger, status="running")
    session.add(run)
    await session.commit()
    run_id = run.id
    stats = RunStats()

    try:
        async with httpx.AsyncClient(headers={"User-Agent": cfg.user_agent}) as http:
            sources = (
                await session.scalars(select(Source).where(Source.enabled.is_(True)))
            ).all()

            for src in sources:
                try:
                    items = await _fetch_source_items(http, src, cfg)
                    stats.fetched += len(items)
                    inserted = await persist_items(session, src.id, items)
                    stats.persisted += inserted
                except Exception:
                    logger.exception("fetch failed for %s", src.slug)
                    stats.errors_per_source[src.slug] = (
                        stats.errors_per_source.get(src.slug, 0) + 1
                    )

            extract_stats = await _extract_for_articles(session, http, cfg)
            stats.extracted = extract_stats.get("updated", 0)

            client = openai_client or AsyncOpenAI()
            embed_stats = await _embed_pending_articles(session, client, cfg)
            stats.embedded = embed_stats.get("embedded", 0)

            cluster_stats = await cluster_recent_articles(
                session,
                threshold=cfg.similarity_threshold,
                window_hours=cfg.window_hours,
            )
            stats.clustered = cluster_stats.get("clustered", 0)
            stats.new_clusters = cluster_stats.get("new_clusters", 0)

            await rank_top_clusters(session, top_n=cfg.top_n)

            analyze_stats = await _analyze_top_clusters(session, client, cfg)
            stats.analyzed = analyze_stats.get("analyzed", 0)

        final_status = "partial" if stats.errors_per_source else "success"
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                status=final_status,
                finished_at=datetime.now(UTC),
                stats=stats.dump(),
            )
        )
        await session.commit()
        return run_id

    except Exception as exc:
        logger.exception("pipeline failed")
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                status="failed",
                finished_at=datetime.now(UTC),
                stats=stats.dump(),
                error=str(exc),
            )
        )
        await session.commit()
        raise


async def _fetch_source_items(
    http: httpx.AsyncClient, source: Source, cfg: PipelineConfig
) -> list:
    cutoff = datetime.now(UTC) - timedelta(hours=cfg.window_hours)
    xml = await fetch_feed(http, source.rss_url)
    return parse_feed(xml, since=cutoff)


async def _extract_for_articles(
    session: AsyncSession, http: httpx.AsyncClient, cfg: PipelineConfig
) -> dict:
    pending = (
        await session.scalars(
            select(Article).where(Article.content.is_(None)).limit(200)
        )
    ).all()
    updated = 0
    for article in pending:
        result = await extract_content(http, article.url)
        article.content = result.content
        article.has_full_text = result.has_full_text
        updated += 1
    await session.commit()
    return {"updated": updated}


async def _embed_pending_articles(
    session: AsyncSession, client: AsyncOpenAI, cfg: PipelineConfig
) -> dict:
    pending = (
        await session.scalars(
            select(Article).where(Article.embedding.is_(None)).limit(500)
        )
    ).all()
    if not pending:
        return {"embedded": 0}
    inputs = [
        build_embedding_input(title=a.title, content=a.content, summary=a.summary)
        for a in pending
    ]
    vectors = await embed_texts(client, inputs, model=cfg.embedding_model)
    for article, vec in zip(pending, vectors, strict=True):
        article.embedding = vec
    await session.commit()
    return {"embedded": len(pending)}


async def _analyze_top_clusters(
    session: AsyncSession, client: AsyncOpenAI, cfg: PipelineConfig
) -> dict:
    clusters = (
        await session.scalars(select(Cluster).where(Cluster.is_top.is_(True)))
    ).all()
    analyzed = 0
    for cluster in clusters:
        existing = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == cluster.id)
        )
        if existing and existing.generated_at >= cluster.last_seen_at:
            continue
        articles = (
            await session.scalars(
                select(Article)
                .where(Article.cluster_id == cluster.id)
                .order_by(Article.published_at)
            )
        ).all()
        payload = []
        for art in articles:
            src = await session.get(Source, art.source_id)
            body = (art.content or art.summary or "")[:3000]
            payload.append({"slug": src.slug, "title": art.title, "body": body})
        result = await analyze_cluster(
            client, articles=payload, model=cfg.analysis_model
        )
        if result is None:
            continue
        if existing:
            existing.headline = result.headline
            existing.common_facts = result.common_facts
            existing.by_source = {k: v.model_dump() for k, v in result.by_source.items()}
            existing.omissions = [o.model_dump() for o in result.omissions]
            existing.divergences = [d.model_dump() for d in result.divergences]
            existing.model = cfg.analysis_model
            existing.prompt_version = prompt_version()
            existing.generated_at = datetime.now(UTC)
        else:
            session.add(
                Analysis(
                    cluster_id=cluster.id,
                    headline=result.headline,
                    common_facts=result.common_facts,
                    by_source={k: v.model_dump() for k, v in result.by_source.items()},
                    omissions=[o.model_dump() for o in result.omissions],
                    divergences=[d.model_dump() for d in result.divergences],
                    model=cfg.analysis_model,
                    prompt_version=prompt_version(),
                )
            )
        analyzed += 1
    await session.commit()
    return {"analyzed": analyzed}
