"""Saga clustering: third-level grouping of clusters over a 7-day window.

Groups clusters whose centroids are similar (cosine >= threshold) into "sagas"
— overarching multi-day story threads.
"""
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Saga
from noticias_api.pipeline.cluster import _UnionFind  # reuse union-find

logger = logging.getLogger(__name__)


async def assign_sagas(
    session: AsyncSession, *, threshold: float, window_hours: int
) -> dict[str, int]:
    """Group clusters in the window into sagas via centroid similarity.

    Algorithm:
    1. Pull clusters in the window with non-null centroids.
    2. Build similarity graph: edge between i,j when cosine_sim >= threshold.
    3. Connected components (union-find) define groupings.
    4. For each component with size >= 2:
       - If any member already has saga_id: reuse the smallest such id (merge sagas if multiple).
       - Else: create a new saga; title from the newest cluster's analysis headline.
       - Set all members' saga_id to that.
    5. Recompute saga aggregates (centroid, counts, dates, title).
    6. Delete sagas left with zero clusters.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    clusters = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.last_seen_at >= cutoff)
            .where(Cluster.centroid.is_not(None))
        )
    ).all()

    if len(clusters) < 2:
        # Even with 0-1 clusters in window, clear saga_id from in-window singletons
        # and disband any sagas that no longer have enough in-window members.
        for c in clusters:
            if c.saga_id is not None:
                await session.execute(
                    update(Cluster).where(Cluster.saga_id == c.saga_id).values(saga_id=None)
                )
        if clusters:
            await session.commit()
        await _cleanup_empty_sagas(session)
        return {"clusters_in_sagas": 0, "active_sagas": 0}

    cluster_ids = sorted(c.id for c in clusters)
    cluster_by_id = {c.id: c for c in clusters}

    matrix = np.stack(
        [np.asarray(cluster_by_id[cid].centroid, dtype=np.float32) for cid in cluster_ids],
        axis=0,
    )
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe = np.where(norms == 0, 1.0, norms)
    normalized = matrix / safe
    sims = normalized @ normalized.T

    uf = _UnionFind(cluster_ids)
    for i in range(len(cluster_ids)):
        for j in range(i + 1, len(cluster_ids)):
            if float(sims[i, j]) >= threshold:
                uf.union(cluster_ids[i], cluster_ids[j])

    components: dict[int, list[int]] = defaultdict(list)
    for cid in cluster_ids:
        components[uf.find(cid)].append(cid)

    saga_to_assign: dict[int, int] = {}  # cluster_id -> saga_id
    saga_to_clear: set[int] = set()  # cluster_ids that should have saga_id set to NULL
    sagas_to_disband: set[int] = set()  # saga_ids whose entire membership must be cleared

    for component in components.values():
        if len(component) < 2:
            # Singleton — disband the whole saga (includes out-of-window members)
            cid = component[0]
            if cluster_by_id[cid].saga_id is not None:
                sagas_to_disband.add(cluster_by_id[cid].saga_id)
            continue

        members = [cluster_by_id[cid] for cid in component]
        existing_saga_ids = {m.saga_id for m in members if m.saga_id is not None}

        if existing_saga_ids:
            saga_id = min(existing_saga_ids)
            redundant = existing_saga_ids - {saga_id}
            if redundant:
                # Re-point clusters from absorbed sagas to canonical
                await session.execute(
                    update(Cluster)
                    .where(Cluster.saga_id.in_(redundant))
                    .values(saga_id=saga_id)
                )
                await session.execute(delete(Saga).where(Saga.id.in_(redundant)))
        else:
            # Create new saga; title = headline of newest cluster
            newest = max(
                members,
                key=lambda c: c.last_seen_at or datetime.min.replace(tzinfo=UTC),
            )
            analysis = await session.scalar(
                select(Analysis).where(Analysis.cluster_id == newest.id)
            )
            title = (
                analysis.headline
                if analysis and analysis.headline
                else f"Saga (cluster {newest.id})"
            )
            saga = Saga(title=title)
            session.add(saga)
            await session.flush()
            saga_id = saga.id

        for cid in component:
            saga_to_assign[cid] = saga_id

    if saga_to_assign:
        for cid, sid in saga_to_assign.items():
            if cluster_by_id[cid].saga_id != sid:
                await session.execute(
                    update(Cluster).where(Cluster.id == cid).values(saga_id=sid)
                )

    # Disband sagas where all in-window members became singletons.
    # Clear ALL members (including out-of-window ones) so the saga can be deleted.
    if sagas_to_disband:
        # But only disband a saga if it wasn't also re-assigned in saga_to_assign
        assigned_sagas = set(saga_to_assign.values())
        truly_disbanded = sagas_to_disband - assigned_sagas
        if truly_disbanded:
            await session.execute(
                update(Cluster)
                .where(Cluster.saga_id.in_(truly_disbanded))
                .values(saga_id=None)
            )

    if saga_to_clear:
        await session.execute(
            update(Cluster)
            .where(Cluster.id.in_(saga_to_clear))
            .values(saga_id=None)
        )

    await session.commit()

    # Refresh aggregates for affected sagas
    affected_saga_ids: set[int] = set(saga_to_assign.values())
    if affected_saga_ids:
        await _refresh_saga_stats(session, affected_saga_ids)

    await _cleanup_empty_sagas(session)

    return {
        "clusters_in_sagas": len(saga_to_assign),
        "active_sagas": len(affected_saga_ids),
    }


async def _refresh_saga_stats(session: AsyncSession, saga_ids: set[int]) -> None:
    for sid in saga_ids:
        clusters = (
            await session.scalars(select(Cluster).where(Cluster.saga_id == sid))
        ).all()
        if not clusters:
            continue
        total_articles = sum(c.article_count for c in clusters)
        sources_count = await session.scalar(
            select(func.count(func.distinct(Article.source_id)))
            .where(Article.cluster_id.in_([c.id for c in clusters]))
        )
        centroids = [
            np.asarray(c.centroid, dtype=np.float32)
            for c in clusters
            if c.centroid is not None
        ]
        new_centroid = (
            np.mean(np.stack(centroids), axis=0).tolist() if centroids else None
        )
        first_seen = min(
            c.first_seen_at for c in clusters if c.first_seen_at is not None
        )
        last_seen = max(
            c.last_seen_at for c in clusters if c.last_seen_at is not None
        )
        # Title: headline of newest cluster's analysis (if any)
        newest = max(
            clusters,
            key=lambda c: c.last_seen_at or datetime.min.replace(tzinfo=UTC),
        )
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == newest.id)
        )
        update_data: dict = {
            "cluster_count": len(clusters),
            "article_count": total_articles,
            "source_count": int(sources_count or 0),
            "first_seen_at": first_seen,
            "last_seen_at": last_seen,
        }
        if new_centroid is not None:
            update_data["centroid"] = new_centroid
        if analysis and analysis.headline:
            update_data["title"] = analysis.headline
        await session.execute(
            update(Saga).where(Saga.id == sid).values(**update_data)
        )
    await session.commit()


async def _cleanup_empty_sagas(session: AsyncSession) -> None:
    used_saga_ids = (
        await session.scalars(
            select(Cluster.saga_id).where(Cluster.saga_id.is_not(None)).distinct()
        )
    ).all()
    if used_saga_ids:
        await session.execute(
            delete(Saga).where(~Saga.id.in_(used_saga_ids))
        )
    else:
        await session.execute(delete(Saga))
    await session.commit()
