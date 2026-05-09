from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Cluster, Source
from noticias_api.pipeline.cluster import cluster_recent_articles


def _vec(value: float, dim: int = 1536) -> list[float]:
    """Create a unit-ish vector pointing in a 'direction'."""
    v = [value] + [0.001] * (dim - 1)
    return v


@pytest.mark.asyncio
async def test_similar_articles_share_cluster(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    a = Article(source_id=src.id, external_id="a", url="u1", title="Inflación",
                embedding=_vec(1.0), published_at=now)
    b = Article(source_id=src.id, external_id="b", url="u2", title="Inflacion",
                embedding=_vec(1.0), published_at=now)
    db_session.add_all([a, b])
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    rows = (await db_session.scalars(select(Article).order_by(Article.id))).all()
    assert rows[0].cluster_id is not None
    assert rows[0].cluster_id == rows[1].cluster_id


@pytest.mark.asyncio
async def test_dissimilar_articles_get_separate_clusters(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    inflation = [1.0] + [0.0] * 1535
    soccer = [0.0] * 1535 + [1.0]
    a = Article(source_id=src.id, external_id="a", url="u1", title="Inflación",
                embedding=inflation, published_at=now)
    b = Article(source_id=src.id, external_id="b", url="u2", title="Boca-River",
                embedding=soccer, published_at=now)
    db_session.add_all([a, b])
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    rows = (await db_session.scalars(select(Article).order_by(Article.id))).all()
    assert rows[0].cluster_id != rows[1].cluster_id


@pytest.mark.asyncio
async def test_articles_outside_window_are_not_clustered(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    old = datetime.now(UTC) - timedelta(hours=72)
    a = Article(source_id=src.id, external_id="a", url="u1", title="x",
                embedding=_vec(1.0), published_at=old)
    db_session.add(a)
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    refreshed = await db_session.get(Article, a.id)
    assert refreshed.cluster_id is None
