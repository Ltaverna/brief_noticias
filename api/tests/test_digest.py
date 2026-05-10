from datetime import UTC, date, datetime

import httpx
import pytest

from noticias_api.config import Settings
from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.notifiers.digest import build_digest, send_digest


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


@pytest.mark.asyncio
async def test_build_digest_empty(db_session):
    msg = await build_digest(db_session, date.today(), "http://x")
    assert "Briefing" in msg
    assert "No hay briefing" in msg


@pytest.mark.asyncio
async def test_build_digest_with_clusters(db_session):
    src = Source(
        slug="ln",
        name="LN",
        editorial_group="mainstream",
        rss_url="x",
        base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    today = date.today()
    cluster = Cluster(
        article_count=2,
        source_count=2,
        last_seen_at=datetime.now(UTC),
        rank_score=5.0,
        is_top=True,
        display_date=today,
    )
    db_session.add(cluster)
    await db_session.commit()

    db_session.add(
        Article(
            source_id=src.id,
            external_id="a1",
            url="https://x/a",
            title="t",
            cluster_id=cluster.id,
            published_at=datetime.now(UTC),
        )
    )
    db_session.add(
        Analysis(
            cluster_id=cluster.id,
            headline="Test headline 4.2%",
            common_facts=[],
            by_source={},
            omissions=[],
            divergences=[],
            model="gpt-4o",
            prompt_version="v2",
        )
    )
    await db_session.commit()

    msg = await build_digest(db_session, today, "http://localhost:3000")
    # Verify the headline appears with MarkdownV2 escaping ('.' -> '\.')
    assert "Test headline 4\\.2%" in msg
    # Link is present
    assert f"http://localhost:3000/cluster/{cluster.id}" in msg


@pytest.mark.asyncio
async def test_send_digest_skipped_when_disabled(db_session):
    settings = make_settings(enable_telegram=False)
    result = await send_digest(db_session, settings, date.today())
    assert result is None


@pytest.mark.asyncio
async def test_send_digest_idempotent(db_session, respx_mock):
    src = Source(
        slug="ln",
        name="LN",
        editorial_group="mainstream",
        rss_url="x",
        base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    today = date.today()
    cluster = Cluster(
        article_count=1,
        source_count=1,
        last_seen_at=datetime.now(UTC),
        rank_score=5.0,
        is_top=True,
        display_date=today,
    )
    db_session.add(cluster)
    await db_session.commit()
    db_session.add(
        Analysis(
            cluster_id=cluster.id,
            headline="Headline",
            common_facts=[],
            by_source={},
            omissions=[],
            divergences=[],
            model="gpt-4o",
            prompt_version="v2",
        )
    )
    await db_session.commit()

    route = respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(
            200, json={"ok": True, "result": {"message_id": 42}}
        )
    )
    settings = make_settings()

    msg_id_1 = await send_digest(db_session, settings, today)
    msg_id_2 = await send_digest(db_session, settings, today)

    assert msg_id_1 == 42
    assert msg_id_2 is None
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_send_digest_force_resends(db_session, respx_mock):
    src = Source(
        slug="ln",
        name="LN",
        editorial_group="mainstream",
        rss_url="x",
        base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    today = date.today()
    cluster = Cluster(
        article_count=1,
        source_count=1,
        last_seen_at=datetime.now(UTC),
        rank_score=5.0,
        is_top=True,
        display_date=today,
    )
    db_session.add(cluster)
    await db_session.commit()
    db_session.add(
        Analysis(
            cluster_id=cluster.id,
            headline="Headline",
            common_facts=[],
            by_source={},
            omissions=[],
            divergences=[],
            model="gpt-4o",
            prompt_version="v2",
        )
    )
    await db_session.commit()

    route = respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(
            200, json={"ok": True, "result": {"message_id": 1}}
        )
    )
    settings = make_settings()

    await send_digest(db_session, settings, today)
    await send_digest(db_session, settings, today, force=True)
    assert route.call_count == 2
