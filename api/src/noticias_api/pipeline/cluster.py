import logging
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster

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


class _UnionFind:
    """Union-find / disjoint-set with path compression. Canonical is smallest id."""

    def __init__(self, items: list[int]) -> None:
        self._parent: dict[int, int] = {x: x for x in items}

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if ra < rb:
            self._parent[rb] = ra
        else:
            self._parent[ra] = rb


async def merge_close_clusters(
    session: AsyncSession,
    *,
    threshold: float,
    window_hours: int,
) -> dict[str, int]:
    """Second pass: merge clusters whose centroids are similar above `threshold`.

    Centroids are recomputed as the mean of each cluster's article embeddings.
    Uses union-find to handle transitive merges. Smallest cluster id is canonical.
    Absorbed clusters' analyses are deleted (via cascade) so the next analyze
    step regenerates them with the merged article set.

    Returns: dict with 'merged' (count of clusters absorbed).
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    candidates = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.last_seen_at >= cutoff)
        )
    ).all()

    if len(candidates) < 2:
        return {"merged": 0}

    # Recompute centroids in Python from current member articles.
    centroids: dict[int, np.ndarray] = {}
    for c in candidates:
        embeds = (
            await session.scalars(
                select(Article.embedding)
                .where(Article.cluster_id == c.id)
                .where(Article.embedding.is_not(None))
            )
        ).all()
        if not embeds:
            continue
        centroids[c.id] = np.mean(np.asarray(embeds, dtype=np.float32), axis=0)

    cluster_ids = sorted(centroids.keys())
    if len(cluster_ids) < 2:
        # Persist whatever centroids we did compute, then bail.
        for cid, vec in centroids.items():
            await session.execute(
                update(Cluster).where(Cluster.id == cid).values(centroid=vec.tolist())
            )
        await session.commit()
        return {"merged": 0}

    # Pairwise cosine sim. n is small (typically <100); O(n^2) is fine.
    matrix = np.stack([centroids[cid] for cid in cluster_ids], axis=0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe = np.where(norms == 0, 1.0, norms)
    normalized = matrix / safe
    sims = normalized @ normalized.T

    uf = _UnionFind(cluster_ids)
    for i in range(len(cluster_ids)):
        for j in range(i + 1, len(cluster_ids)):
            if float(sims[i, j]) >= threshold:
                uf.union(cluster_ids[i], cluster_ids[j])

    # Persist updated centroids first (so even non-merged clusters benefit from refresh)
    for cid, vec in centroids.items():
        await session.execute(
            update(Cluster).where(Cluster.id == cid).values(centroid=vec.tolist())
        )

    # Apply merges.
    merged = 0
    for cid in cluster_ids:
        canonical = uf.find(cid)
        if canonical == cid:
            continue
        # Reassign articles
        await session.execute(
            update(Article)
            .where(Article.cluster_id == cid)
            .values(cluster_id=canonical)
        )
        # Drop the absorbed cluster (Analysis cascades via FK ondelete='CASCADE')
        await session.execute(delete(Cluster).where(Cluster.id == cid))
        merged += 1

    if merged:
        # Force re-analysis on canonical clusters that absorbed others by
        # nuking their existing analyses (the merged set has new content).
        canonical_ids = {uf.find(cid) for cid in cluster_ids if uf.find(cid) != cid}
        if canonical_ids:
            await session.execute(
                delete(Analysis).where(Analysis.cluster_id.in_(canonical_ids))
            )

    await session.commit()
    await _refresh_cluster_stats(session, cutoff)
    return {"merged": merged}


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
