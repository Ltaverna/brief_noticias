from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Cluster, Source
from noticias_api.pipeline.rank import rank_top_clusters


@pytest.mark.asyncio
async def test_rank_marks_top_n_with_highest_score(db_session):
    sources = [
        Source(slug=f"s{i}", name=f"S{i}", editorial_group="mainstream",
               rss_url="x", base_url="x")
        for i in range(5)
    ]
    db_session.add_all(sources)
    await db_session.commit()

    now = datetime.now(UTC)
    # cluster A: 4 sources, recent → high score
    cluster_a = Cluster(article_count=4, source_count=4, last_seen_at=now)
    # cluster B: 2 sources, recent → medium
    cluster_b = Cluster(article_count=2, source_count=2, last_seen_at=now)
    # cluster C: 1 source → filtered out (below source_count >= 2)
    cluster_c = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([cluster_a, cluster_b, cluster_c])
    await db_session.commit()

    await rank_top_clusters(db_session, top_n=10)

    rows = (await db_session.scalars(select(Cluster).where(Cluster.is_top))).all()
    top_ids = {r.id for r in rows}
    assert cluster_a.id in top_ids
    assert cluster_b.id in top_ids
    assert cluster_c.id not in top_ids  # filtered by min source_count


@pytest.mark.asyncio
async def test_rank_respects_top_n_cap(db_session):
    src = Source(slug="s", name="S", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    clusters = [
        Cluster(article_count=2, source_count=2, last_seen_at=now - timedelta(hours=i))
        for i in range(20)
    ]
    db_session.add_all(clusters)
    await db_session.commit()

    await rank_top_clusters(db_session, top_n=5)

    from sqlalchemy import func as sa_func
    top_count = await db_session.scalar(
        select(sa_func.count(Cluster.id)).where(Cluster.is_top)
    )
    assert top_count == 5
