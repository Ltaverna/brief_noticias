from datetime import UTC, date, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.seed import seed_sources


@pytest.mark.asyncio
async def test_get_today_briefing_returns_top_clusters_only(db_session, client):
    await seed_sources(db_session)
    today = date.today()
    now = datetime.now(UTC)

    top = Cluster(
        article_count=4, source_count=4, last_seen_at=now,
        rank_score=10.0, is_top=True, display_date=today,
    )
    not_top = Cluster(
        article_count=1, source_count=1, last_seen_at=now,
        rank_score=1.0, is_top=False, display_date=None,  # not assigned to a briefing
    )
    db_session.add_all([top, not_top])
    await db_session.commit()

    db_session.add(Analysis(
        cluster_id=top.id, headline="Test headline",
        common_facts=["a", "b"], by_source={}, omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v1",
    ))
    await db_session.commit()

    response = client.get("/briefings/today")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == today.isoformat()
    assert len(body["clusters"]) == 1
    assert body["clusters"][0]["headline"] == "Test headline"


@pytest.mark.asyncio
async def test_get_briefing_by_date_works_even_after_is_top_was_reset(db_session, client):
    """Regression: historical briefings should not depend on is_top flag.
    A new pipeline run resets is_top globally, but display_date persists."""
    await seed_sources(db_session)
    target = date(2026, 4, 1)
    now = datetime.now(UTC)
    # cluster from 2026-04-01 — yesterday's run flipped is_top off but display_date stays
    c = Cluster(article_count=3, source_count=3, last_seen_at=now,
                rank_score=5.0, is_top=False, display_date=target)
    db_session.add(c)
    await db_session.commit()

    response = client.get(f"/briefings/{target.isoformat()}")
    assert response.status_code == 200
    assert len(response.json()["clusters"]) == 1


@pytest.mark.asyncio
async def test_list_briefing_dates(db_session, client):
    now = datetime.now(UTC)
    for d in [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)]:
        c = Cluster(article_count=2, source_count=2, last_seen_at=now,
                    rank_score=1.0, is_top=False, display_date=d)
        db_session.add(c)
    await db_session.commit()

    response = client.get("/briefings")
    assert response.status_code == 200
    dates = response.json()
    assert len(dates) == 3
    assert dates[0] == "2026-05-03"  # newest first
