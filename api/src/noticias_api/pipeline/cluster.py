import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article, Cluster

logger = logging.getLogger(__name__)


async def cluster_recent_articles(
    session: AsyncSession, *, threshold: float, window_hours: int
) -> dict[str, int]:
    """Assign cluster_id to articles in the time window using kNN over embeddings.

    Algorithm: for each article without a cluster, find the most similar article
    in the window that already has a cluster. If similarity >= threshold, join
    that cluster. Otherwise, create a new cluster. Cosine similarity = 1 - cosine_distance.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    new_articles = (
        await session.scalars(
            select(Article)
            .where(Article.published_at >= cutoff)
            .where(Article.cluster_id.is_(None))
            .where(Article.embedding.is_not(None))
            .order_by(Article.published_at)
        )
    ).all()

    stats = {"clustered": 0, "new_clusters": 0}

    for article in new_articles:
        # find nearest neighbor with a cluster, within window
        nearest = await session.execute(
            select(
                Article.cluster_id,
                (1 - Article.embedding.cosine_distance(article.embedding)).label("sim"),
            )
            .where(Article.id != article.id)
            .where(Article.published_at >= cutoff)
            .where(Article.cluster_id.is_not(None))
            .where(Article.embedding.is_not(None))
            .order_by(Article.embedding.cosine_distance(article.embedding))
            .limit(1)
        )
        row = nearest.first()

        if row and row.sim >= threshold:
            article.cluster_id = row.cluster_id
        else:
            new_cluster = Cluster(centroid=article.embedding)
            session.add(new_cluster)
            await session.flush()
            article.cluster_id = new_cluster.id
            stats["new_clusters"] += 1
        stats["clustered"] += 1

    await session.commit()
    await _refresh_cluster_stats(session, cutoff)
    return stats


async def _refresh_cluster_stats(session: AsyncSession, cutoff: datetime) -> None:
    """Recompute article_count, source_count, last_seen_at for affected clusters."""
    cluster_ids = (
        await session.scalars(
            select(Article.cluster_id)
            .where(Article.cluster_id.is_not(None))
            .where(Article.published_at >= cutoff)
            .distinct()
        )
    ).all()

    for cid in cluster_ids:
        agg = (
            await session.execute(
                select(
                    func.count(Article.id).label("ac"),
                    func.count(func.distinct(Article.source_id)).label("sc"),
                    func.max(Article.published_at).label("last"),
                ).where(Article.cluster_id == cid)
            )
        ).one()
        await session.execute(
            update(Cluster)
            .where(Cluster.id == cid)
            .values(article_count=agg.ac, source_count=agg.sc, last_seen_at=agg.last)
        )
    await session.commit()
