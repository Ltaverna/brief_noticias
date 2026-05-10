from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.config import Settings
from noticias_api.db.models import Article, Cluster, Source
from noticias_api.notifiers.bot_handler import (
    allowed_chats,
    format_qa_response,
    handle_update,
)
from noticias_api.qa.retrieval import RetrievedChunk


def make_settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql+psycopg://x:x@h:5432/d",
        openai_api_key="sk-x",
        telegram_bot_token=":ABC",
        telegram_chat_id="42",
        enable_telegram=True,
    )
    base.update(overrides)
    return Settings(**base)


# ---------------------------------------------------------------------------
# allowed_chats
# ---------------------------------------------------------------------------

def test_allowed_chats_falls_back_to_chat_id():
    s = make_settings()
    assert allowed_chats(s) == {"42"}


def test_allowed_chats_uses_csv_when_set():
    s = make_settings(telegram_allowed_chats="1, 2 ,3")
    assert allowed_chats(s) == {"1", "2", "3"}


def test_allowed_chats_empty_when_no_token_or_csv():
    s = make_settings(telegram_chat_id=None)
    assert allowed_chats(s) == set()


# ---------------------------------------------------------------------------
# format_qa_response
# ---------------------------------------------------------------------------

def _make_chunk(n: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        article_id=n,
        cluster_id=1,
        source_slug="ln",
        source_name="La Nación",
        title="Título de prueba",
        url=f"https://example.com/{n}",
        published_at=datetime(2026, 5, 9, tzinfo=UTC),
        text="texto cuerpo",
        snippet="snippet",
    )


def test_format_qa_response_includes_answer():
    chunk = _make_chunk()
    msg = format_qa_response("pregunta", "La respuesta es X [1].", [1], [chunk])
    assert "La respuesta es X" in msg


def test_format_qa_response_includes_source_url():
    chunk = _make_chunk()
    msg = format_qa_response("q", "respuesta [1].", [1], [chunk])
    assert "https://example.com/1" in msg


def test_format_qa_response_no_citations():
    chunk = _make_chunk()
    msg = format_qa_response("q", "respuesta sin citas.", [], [chunk])
    assert "Fuentes" not in msg


def test_format_qa_response_truncates_long_message():
    chunk = _make_chunk()
    long_answer = "x" * 5000
    msg = format_qa_response("q", long_answer, [], [chunk])
    assert len(msg) <= 4000


def test_format_qa_response_ignores_out_of_range_citation():
    chunk = _make_chunk()
    # citation [5] references chunk 5, but we only have 1 chunk
    msg = format_qa_response("q", "respuesta [5].", [5], [chunk])
    # Should not crash; [5] silently ignored since n > len(chunks)
    assert "Fuentes" not in msg


# ---------------------------------------------------------------------------
# handle_update — unit tests (no DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_update_ignores_non_message():
    settings = make_settings()
    update = {"some_other_field": {}}
    session = MagicMock()
    # Should not raise, simply return
    await handle_update(update, settings=settings, session=session)


@pytest.mark.asyncio
async def test_handle_update_ignores_missing_chat_id():
    settings = make_settings()
    update = {"message": {"chat": {}, "text": "hola"}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)


@pytest.mark.asyncio
async def test_handle_update_rejects_unauthorized_chat(monkeypatch):
    settings = make_settings(telegram_chat_id="42")
    sent: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))
            return 1

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    update = {"message": {"chat": {"id": 999}, "text": "hola"}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)
    assert sent == []  # not authorized → no send


@pytest.mark.asyncio
async def test_handle_update_responds_to_start(monkeypatch):
    settings = make_settings()
    sent: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))
            return 1

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    update = {"message": {"chat": {"id": 42}, "text": "/start"}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)
    assert sent
    assert "Noticias" in sent[0][1]


@pytest.mark.asyncio
async def test_handle_update_responds_to_help(monkeypatch):
    settings = make_settings()
    sent: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))
            return 1

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    update = {"message": {"chat": {"id": 42}, "text": "/help"}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)
    assert sent
    assert "/start" in sent[0][1] or "Comandos" in sent[0][1]


@pytest.mark.asyncio
async def test_handle_update_unknown_command(monkeypatch):
    settings = make_settings()
    sent: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))
            return 1

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    update = {"message": {"chat": {"id": 42}, "text": "/unknown"}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)
    assert sent
    assert "no reconocido" in sent[0][1] or "help" in sent[0][1].lower()


@pytest.mark.asyncio
async def test_handle_update_ignores_empty_text(monkeypatch):
    settings = make_settings()
    sent: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))
            return 1

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    update = {"message": {"chat": {"id": 42}, "text": "   "}}
    session = MagicMock()
    await handle_update(update, settings=settings, session=session)
    assert sent == []


# ---------------------------------------------------------------------------
# handle_update — integration test with DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_update_runs_qa_for_text(db_session, monkeypatch):
    settings = make_settings()

    src = Source(
        slug="ln", name="LN", editorial_group="mainstream",
        rss_url="x", base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    cluster = Cluster(
        article_count=1, source_count=1, last_seen_at=datetime.now(UTC)
    )
    db_session.add(cluster)
    await db_session.commit()

    db_session.add(Article(
        source_id=src.id, external_id="a1", url="https://x/a1", title="t",
        embedding=[1.0] + [0.0] * 1535,
        published_at=datetime.now(UTC), cluster_id=cluster.id,
    ))
    await db_session.commit()

    sends: list = []
    edits: list = []

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            sends.append((chat_id, text))
            return 100

        async def edit_message_text(self, chat_id, message_id, text, **kwargs):
            edits.append((chat_id, message_id, text))

    fake_oai = MagicMock()
    fake_emb = MagicMock()
    fake_emb.data = [MagicMock(embedding=[1.0] + [0.0] * 1535)]
    fake_oai.embeddings.create = AsyncMock(return_value=fake_emb)
    fake_chat = MagicMock()
    fake_chat.choices = [
        MagicMock(message=MagicMock(content="Respuesta de prueba [1]."))
    ]
    fake_oai.chat.completions.create = AsyncMock(return_value=fake_chat)

    monkeypatch.setattr("noticias_api.notifiers.bot_handler.TelegramClient", FakeBot)
    monkeypatch.setattr(
        "noticias_api.notifiers.bot_handler.AsyncOpenAI", lambda **kw: fake_oai
    )

    update = {"message": {"chat": {"id": 42}, "text": "qué pasó"}}
    await handle_update(update, settings=settings, session=db_session)

    assert sends, "placeholder message should have been sent"
    assert edits, "final answer should have been sent via edit_message_text"
    assert "Respuesta de prueba" in edits[-1][2]
