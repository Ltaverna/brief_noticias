"""Tests for A3 alert detection and delivery."""
from datetime import UTC, date, datetime

import httpx
import pytest

from noticias_api.config import Settings
from noticias_api.db.models import (
    AlertDelivery,
    Analysis,
    Article,
    Cluster,
    ClusterEntity,
    Entity,
    Source,
    Subscription,
)
from noticias_api.notifiers.alerts import detect_and_send_alerts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql+psycopg://x:x@h:5432/d",
        openai_api_key="sk-x",
        telegram_bot_token=":ABC",
        telegram_chat_id="999",
        enable_telegram=True,
        public_base_url="http://localhost:3000",
    )
    base.update(overrides)
    return Settings(**base)


async def _make_source(session, slug="ln") -> Source:
    src = Source(
        slug=slug, name=slug.upper(),
        editorial_group="mainstream", rss_url="x", base_url="x",
    )
    session.add(src)
    await session.commit()
    return src


async def _make_cluster(session, source_count=5) -> Cluster:
    c = Cluster(
        article_count=source_count,
        source_count=source_count,
        last_seen_at=datetime.now(UTC),
        rank_score=5.0,
        is_top=True,
        display_date=date.today(),
    )
    session.add(c)
    await session.commit()
    return c


async def _make_entity(session, canonical: str) -> Entity:
    e = Entity(name=canonical.title(), kind="person", canonical=canonical)
    session.add(e)
    await session.commit()
    return e


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_subs_with_threshold_skips(db_session):
    """No subscriptions with alert threshold → no alerts sent."""
    # Add sub without threshold
    sub = Subscription(channel="telegram", chat_id="999", kind="entity",
                       value="adorni", alert_threshold_sources=None)
    db_session.add(sub)
    await db_session.commit()

    result = await detect_and_send_alerts(db_session, make_settings())
    assert result["alerts_sent"] == 0


@pytest.mark.asyncio
async def test_alerts_disabled_when_telegram_off(db_session):
    settings = make_settings(enable_telegram=False)
    result = await detect_and_send_alerts(db_session, settings)
    assert result["alerts_sent"] == 0


@pytest.mark.asyncio
async def test_entity_alert_sent_when_threshold_met(db_session, respx_mock):
    """Entity subscription with threshold → alert sent for matching cluster."""
    src = await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=5)
    entity = await _make_entity(db_session, "adorni")

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    db_session.add(Analysis(
        cluster_id=cluster.id, headline="Adorni habló",
        common_facts=[], by_source={}, omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v2",
    ))
    db_session.add(Article(
        source_id=src.id, external_id="a1", url="http://x/a",
        title="t", cluster_id=cluster.id, published_at=datetime.now(UTC),
    ))
    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="entity", value="adorni",
        alert_threshold_sources=3,
    )
    db_session.add(sub)
    await db_session.commit()

    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 77}})
    )

    result = await detect_and_send_alerts(db_session, make_settings())
    assert result["alerts_sent"] == 1


@pytest.mark.asyncio
async def test_entity_alert_not_sent_when_below_threshold(db_session, respx_mock):
    """Cluster with source_count < threshold → no alert."""
    src = await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=2)  # below threshold=5
    entity = await _make_entity(db_session, "adorni")

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="entity", value="adorni",
        alert_threshold_sources=5,
    )
    db_session.add(sub)
    await db_session.commit()

    route = respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )

    result = await detect_and_send_alerts(db_session, make_settings())
    assert result["alerts_sent"] == 0
    assert route.call_count == 0


@pytest.mark.asyncio
async def test_alert_idempotent_not_resent(db_session, respx_mock):
    """Second call to detect_and_send_alerts does not resend same alert."""
    src = await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=5)
    entity = await _make_entity(db_session, "adorni")

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="entity", value="adorni",
        alert_threshold_sources=3,
    )
    db_session.add(sub)
    await db_session.commit()

    route = respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )

    settings = make_settings()
    r1 = await detect_and_send_alerts(db_session, settings)
    r2 = await detect_and_send_alerts(db_session, settings)

    assert r1["alerts_sent"] == 1
    assert r2["alerts_sent"] == 0
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_alert_delivery_record_created(db_session, respx_mock):
    """AlertDelivery row is persisted after sending."""
    src = await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=5)
    entity = await _make_entity(db_session, "adorni")

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="entity", value="adorni",
        alert_threshold_sources=3,
    )
    db_session.add(sub)
    await db_session.commit()

    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )

    await detect_and_send_alerts(db_session, make_settings())

    from sqlalchemy import select
    ad = await db_session.scalar(
        select(AlertDelivery).where(AlertDelivery.cluster_id == cluster.id)
    )
    assert ad is not None
    assert ad.status == "sent"
    assert ad.channel == "telegram"


@pytest.mark.asyncio
async def test_all_kind_alert_triggers_for_any_cluster(db_session, respx_mock):
    """'all' kind subscription → alert for any cluster meeting threshold."""
    await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=4)

    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="all", value=None,
        alert_threshold_sources=3,
    )
    db_session.add(sub)
    await db_session.commit()

    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )

    result = await detect_and_send_alerts(db_session, make_settings())
    assert result["alerts_sent"] == 1


@pytest.mark.asyncio
async def test_alert_failure_stored(db_session, respx_mock):
    """When Telegram returns error, AlertDelivery status is 'failed'."""
    await _make_source(db_session)
    cluster = await _make_cluster(db_session, source_count=5)
    entity = await _make_entity(db_session, "adorni")

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=entity.id))
    sub = Subscription(
        channel="telegram", chat_id="999",
        kind="entity", value="adorni",
        alert_threshold_sources=3,
    )
    db_session.add(sub)
    await db_session.commit()

    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(500, text="server error")
    )

    result = await detect_and_send_alerts(db_session, make_settings())
    assert result["alerts_sent"] == 0

    from sqlalchemy import select
    ad = await db_session.scalar(
        select(AlertDelivery).where(AlertDelivery.cluster_id == cluster.id)
    )
    assert ad is not None
    assert ad.status == "failed"
