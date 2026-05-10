"""Tests for D6 subscription-based digest filtering."""
from datetime import UTC, date, datetime

import pytest

from noticias_api.db.models import (
    Analysis,
    Article,
    Cluster,
    ClusterEntity,
    Entity,
    Source,
    Subscription,
)
from noticias_api.notifiers.digest import (
    _load_subscriptions,
    _matching_cluster_ids_for_subs,
    build_digest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_source(session, slug="ln") -> Source:
    src = Source(
        slug=slug, name=slug.upper(),
        editorial_group="mainstream", rss_url="x", base_url="x",
    )
    session.add(src)
    await session.commit()
    return src


async def _make_cluster(session, today, rank=5.0, source_count=2) -> Cluster:
    c = Cluster(
        article_count=source_count,
        source_count=source_count,
        last_seen_at=datetime.now(UTC),
        rank_score=rank,
        is_top=True,
        display_date=today,
    )
    session.add(c)
    await session.commit()
    return c


async def _make_entity(session, canonical: str, kind="person") -> Entity:
    e = Entity(
        name=canonical.title(),
        kind=kind,
        canonical=canonical,
    )
    session.add(e)
    await session.commit()
    return e


# ---------------------------------------------------------------------------
# _load_subscriptions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_subscriptions_empty(db_session):
    subs = await _load_subscriptions(db_session, "telegram", "999")
    assert subs == []


@pytest.mark.asyncio
async def test_load_subscriptions_returns_matching(db_session):
    sub = Subscription(channel="telegram", chat_id="999", kind="entity", value="adorni")
    other = Subscription(channel="telegram", chat_id="other_chat", kind="entity", value="adorni")
    db_session.add(sub)
    db_session.add(other)
    await db_session.commit()

    subs = await _load_subscriptions(db_session, "telegram", "999")
    assert len(subs) == 1
    assert subs[0].value == "adorni"


# ---------------------------------------------------------------------------
# _matching_cluster_ids_for_subs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_subs_returns_none(db_session):
    """No subscriptions → None (no filter)."""
    result = await _matching_cluster_ids_for_subs(db_session, date.today(), [])
    assert result is None


@pytest.mark.asyncio
async def test_all_sub_returns_none(db_session):
    """'all' subscription → None (no filter)."""
    sub = Subscription(channel="telegram", chat_id="999", kind="all", value=None)
    subs = [sub]
    result = await _matching_cluster_ids_for_subs(db_session, date.today(), subs)
    assert result is None


@pytest.mark.asyncio
async def test_entity_sub_matches_cluster(db_session):
    today = date.today()
    src = await _make_source(db_session)
    cluster_match = await _make_cluster(db_session, today)
    cluster_no_match = await _make_cluster(db_session, today)

    entity = await _make_entity(db_session, "manuel adorni")

    # Link entity to cluster_match only
    db_session.add(ClusterEntity(cluster_id=cluster_match.id, entity_id=entity.id))
    await db_session.commit()

    sub = Subscription(channel="telegram", chat_id="999", kind="entity", value="manuel adorni")
    result = await _matching_cluster_ids_for_subs(db_session, today, [sub])

    assert result is not None
    assert cluster_match.id in result
    assert cluster_no_match.id not in result


@pytest.mark.asyncio
async def test_entity_sub_case_insensitive(db_session):
    """Subscription value is matched case-insensitively against entity.canonical."""
    today = date.today()
    await _make_cluster(db_session, today)
    cluster = await _make_cluster(db_session, today)
    entity = await _make_entity(db_session, "adorni")
    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    await db_session.commit()

    # subscription stored as uppercase (API lowercases, but let's test the filter directly)
    sub = Subscription(channel="telegram", chat_id="999", kind="entity", value="ADORNI")
    result = await _matching_cluster_ids_for_subs(db_session, today, [sub])
    assert result is not None
    assert cluster.id in result


@pytest.mark.asyncio
async def test_entity_sub_no_match_returns_empty_set(db_session):
    """Entity sub with no matching clusters → empty set (not None)."""
    today = date.today()
    sub = Subscription(channel="telegram", chat_id="999", kind="entity", value="unknown entity")
    result = await _matching_cluster_ids_for_subs(db_session, today, [sub])
    assert result is not None
    assert len(result) == 0


# ---------------------------------------------------------------------------
# build_digest with filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_digest_no_filter_includes_all(db_session):
    """cluster_ids_filter=None → all clusters included."""
    today = date.today()
    src = await _make_source(db_session)
    c1 = await _make_cluster(db_session, today, rank=10.0)
    c2 = await _make_cluster(db_session, today, rank=5.0)

    db_session.add(Analysis(cluster_id=c1.id, headline="Headline One",
                             common_facts=[], by_source={}, omissions=[], divergences=[],
                             model="gpt-4o", prompt_version="v2"))
    db_session.add(Analysis(cluster_id=c2.id, headline="Headline Two",
                             common_facts=[], by_source={}, omissions=[], divergences=[],
                             model="gpt-4o", prompt_version="v2"))
    await db_session.commit()

    msg = await build_digest(db_session, today, "http://x", cluster_ids_filter=None)
    assert "Headline One" in msg
    assert "Headline Two" in msg


@pytest.mark.asyncio
async def test_build_digest_with_filter_excludes_non_matching(db_session):
    """cluster_ids_filter={c1.id} → only c1 appears."""
    today = date.today()
    src = await _make_source(db_session)
    c1 = await _make_cluster(db_session, today, rank=10.0)
    c2 = await _make_cluster(db_session, today, rank=5.0)

    db_session.add(Analysis(cluster_id=c1.id, headline="Filtered In",
                             common_facts=[], by_source={}, omissions=[], divergences=[],
                             model="gpt-4o", prompt_version="v2"))
    db_session.add(Analysis(cluster_id=c2.id, headline="Filtered Out",
                             common_facts=[], by_source={}, omissions=[], divergences=[],
                             model="gpt-4o", prompt_version="v2"))
    await db_session.commit()

    msg = await build_digest(db_session, today, "http://x", cluster_ids_filter={c1.id})
    assert "Filtered In" in msg
    assert "Filtered Out" not in msg


@pytest.mark.asyncio
async def test_build_digest_empty_filter_shows_no_briefing(db_session):
    """cluster_ids_filter={} (empty set, not None) → no clusters → empty message."""
    today = date.today()
    await _make_cluster(db_session, today)
    msg = await build_digest(db_session, today, "http://x", cluster_ids_filter=set())
    assert "No hay briefing" in msg
