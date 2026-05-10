from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.pipeline.cluster import merge_close_clusters


def _vec(direction: int, dim: int = 1536) -> list[float]:
    """Unit vector pointing strongly in one of the canonical directions."""
    v = [0.0] * dim
    v[direction % dim] = 1.0
    return v


@pytest.mark.asyncio
async def test_merge_combines_clusters_with_similar_centroids(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    # Two clusters whose member-article embeddings are nearly identical
    c_a = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_b = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    # Articles in cluster A and B that are *very similar* (same vec direction).
    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="u1", title="t1",
                embedding=_vec(0), published_at=now, cluster_id=c_a.id),
        Article(source_id=src.id, external_id="a2", url="u2", title="t2",
                embedding=_vec(0), published_at=now, cluster_id=c_b.id),
    ])
    await db_session.commit()

    a_id, b_id = c_a.id, c_b.id

    stats = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    assert stats["merged"] == 1

    # The smaller-id cluster should be canonical, the other absorbed.
    canonical = min(a_id, b_id)
    absorbed = max(a_id, b_id)

    surviving_articles = (
        await db_session.scalars(select(Article).order_by(Article.id))
    ).all()
    assert all(a.cluster_id == canonical for a in surviving_articles)

    surviving_clusters = (
        await db_session.scalars(select(Cluster.id))
    ).all()
    assert canonical in surviving_clusters
    assert absorbed not in surviving_clusters


@pytest.mark.asyncio
async def test_merge_does_not_combine_dissimilar_clusters(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    c_a = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_b = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    # Orthogonal vectors → cosine sim ≈ 0
    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="u1", title="t1",
                embedding=_vec(0), published_at=now, cluster_id=c_a.id),
        Article(source_id=src.id, external_id="a2", url="u2", title="t2",
                embedding=_vec(500), published_at=now, cluster_id=c_b.id),
    ])
    await db_session.commit()

    stats = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    assert stats["merged"] == 0

    cluster_ids = (await db_session.scalars(select(Cluster.id))).all()
    assert set(cluster_ids) == {c_a.id, c_b.id}


@pytest.mark.asyncio
async def test_merge_deletes_analyses_of_canonical_so_regen_happens(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    c_a = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_b = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="u1", title="t1",
                embedding=_vec(0), published_at=now, cluster_id=c_a.id),
        Article(source_id=src.id, external_id="a2", url="u2", title="t2",
                embedding=_vec(0), published_at=now, cluster_id=c_b.id),
    ])
    db_session.add(Analysis(
        cluster_id=c_a.id, headline="canonical analysis (will be deleted)",
        common_facts=[], by_source={}, omissions=[], divergences=[],
        model="x", prompt_version="v2",
    ))
    await db_session.commit()

    canonical = min(c_a.id, c_b.id)
    await merge_close_clusters(db_session, threshold=0.85, window_hours=72)

    remaining = (
        await db_session.scalars(
            select(Analysis).where(Analysis.cluster_id == canonical)
        )
    ).all()
    assert remaining == []  # deleted to force regen


@pytest.mark.asyncio
async def test_merge_is_idempotent(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    c_a = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_b = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([c_a, c_b])
    await db_session.commit()
    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="u1", title="t1",
                embedding=_vec(0), published_at=now, cluster_id=c_a.id),
        Article(source_id=src.id, external_id="a2", url="u2", title="t2",
                embedding=_vec(0), published_at=now, cluster_id=c_b.id),
    ])
    await db_session.commit()

    s1 = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    s2 = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    assert s1["merged"] == 1
    assert s2["merged"] == 0


@pytest.mark.asyncio
async def test_merge_skips_clusters_outside_window(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    old = datetime.now(UTC) - timedelta(hours=200)
    c_old = Cluster(article_count=1, source_count=1, last_seen_at=old)
    db_session.add(c_old)
    await db_session.commit()
    db_session.add(Article(
        source_id=src.id, external_id="a1", url="u1", title="t1",
        embedding=_vec(0), published_at=old, cluster_id=c_old.id,
    ))
    await db_session.commit()

    stats = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    assert stats["merged"] == 0
    surviving = (await db_session.scalars(select(Cluster.id))).all()
    assert c_old.id in surviving


@pytest.mark.asyncio
async def test_merge_handles_transitive_chains(db_session):
    """A~B at 0.86, B~C at 0.86, A~C at 0.84 → all three should still merge."""
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    c_a = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_b = Cluster(article_count=1, source_count=1, last_seen_at=now)
    c_c = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([c_a, c_b, c_c])
    await db_session.commit()

    # Identical vectors → all sims = 1.0; merge all into smallest id.
    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="u1", title="t1",
                embedding=_vec(0), published_at=now, cluster_id=c_a.id),
        Article(source_id=src.id, external_id="a2", url="u2", title="t2",
                embedding=_vec(0), published_at=now, cluster_id=c_b.id),
        Article(source_id=src.id, external_id="a3", url="u3", title="t3",
                embedding=_vec(0), published_at=now, cluster_id=c_c.id),
    ])
    await db_session.commit()

    stats = await merge_close_clusters(db_session, threshold=0.85, window_hours=72)
    assert stats["merged"] == 2  # b and c absorbed into a

    canonical = min(c_a.id, c_b.id, c_c.id)
    arts = (await db_session.scalars(select(Article))).all()
    assert all(a.cluster_id == canonical for a in arts)
