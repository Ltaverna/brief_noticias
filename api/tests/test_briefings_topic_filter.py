from datetime import UTC, date, datetime

import pytest

from noticias_api.db.models import Cluster, Source


@pytest.fixture
async def two_topics(db_session):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    today = date.today()
    now = datetime.now(UTC)
    cp = Cluster(article_count=1, source_count=1, last_seen_at=now,
                 rank_score=10.0, is_top=True, display_date=today,
                 topic="politica")
    cd = Cluster(article_count=1, source_count=1, last_seen_at=now,
                 rank_score=9.0, is_top=True, display_date=today,
                 topic="deportes")
    db_session.add_all([cp, cd])
    await db_session.commit()
    return cp.id, cd.id


@pytest.mark.asyncio
async def test_today_filters_by_topic(two_topics, client):
    cp_id, cd_id = two_topics
    r = client.get("/briefings/today?topic=politica")
    body = r.json()
    cluster_ids = {c["id"] for c in body["clusters"]}
    assert cp_id in cluster_ids
    assert cd_id not in cluster_ids


@pytest.mark.asyncio
async def test_today_no_filter_returns_all(two_topics, client):
    cp_id, cd_id = two_topics
    r = client.get("/briefings/today")
    cluster_ids = {c["id"] for c in r.json()["clusters"]}
    assert cp_id in cluster_ids
    assert cd_id in cluster_ids


@pytest.mark.asyncio
async def test_briefing_returns_topic_in_summary(two_topics, client):
    r = client.get("/briefings/today")
    topics = {c["topic"] for c in r.json()["clusters"]}
    assert "politica" in topics
    assert "deportes" in topics
