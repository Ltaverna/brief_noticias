from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from noticias_api.db.models import Article, Cluster, Source


def _make_fake_openai(embedding=None, chat_content="Según el INDEC, fue del 4,2% [1]."):
    """Return a MagicMock AsyncOpenAI client with pre-configured responses."""
    emb = embedding or [1.0] + [0.0] * 1535
    fake_client = MagicMock()
    fake_emb = MagicMock()
    fake_emb.data = [MagicMock(embedding=emb)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_emb)
    fake_chat = MagicMock()
    fake_chat.choices = [MagicMock(message=MagicMock(content=chat_content))]
    fake_client.chat.completions.create = AsyncMock(return_value=fake_chat)
    return fake_client


async def _seed_article(db_session):
    """Insert one source, cluster and article; return the source."""
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    now = datetime.now(UTC)
    cluster = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add(cluster)
    await db_session.commit()
    db_session.add(Article(
        source_id=src.id, external_id="a1", url="https://x/a1",
        title="Inflación de abril",
        content="El INDEC informó que la inflación fue del 4,2 por ciento.",
        embedding=[1.0] + [0.0] * 1535,
        published_at=now, cluster_id=cluster.id,
    ))
    await db_session.commit()
    return src


@pytest.mark.asyncio
async def test_qa_returns_answer_with_citations(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    response = client.post("/qa", json={"query": "Cuánto fue la inflación"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Cuánto fue la inflación"
    assert "[1]" in body["answer"]
    assert body["used_citations"] == [1]
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source_slug"] == "ln"


@pytest.mark.asyncio
async def test_qa_response_includes_conversation_id(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    response = client.post("/qa", json={"query": "Cuánto fue la inflación"})
    assert response.status_code == 200
    body = response.json()
    assert "conversation_id" in body
    assert isinstance(body["conversation_id"], str)
    assert len(body["conversation_id"]) > 0


@pytest.mark.asyncio
async def test_qa_new_conversation_id_generated_when_none(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    r1 = client.post("/qa", json={"query": "Cuánto fue la inflación"})
    r2 = client.post("/qa", json={"query": "Cuánto fue la inflación"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Without a conversation_id each request gets a fresh one
    assert r1.json()["conversation_id"] != r2.json()["conversation_id"]


@pytest.mark.asyncio
async def test_qa_uses_provided_conversation_id(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    cid = "my-fixed-conversation-id"
    response = client.post("/qa", json={"query": "Cuánto fue la inflación", "conversation_id": cid})
    assert response.status_code == 200
    assert response.json()["conversation_id"] == cid


@pytest.mark.asyncio
async def test_qa_hyde_called_when_enabled(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    # The fake client's chat.completions.create is called for both HyDE and
    # synthesis when enable_hyde=True (the default). Verify it's called at
    # least twice (once for HyDE, once for synthesis).
    monkeypatch.setenv("ENABLE_HYDE", "true")

    response = client.post("/qa", json={"query": "inflación"})
    assert response.status_code == 200
    # At least two calls: HyDE + synthesis
    assert fake_client.chat.completions.create.await_count >= 2


@pytest.mark.asyncio
async def test_qa_history_endpoint_returns_messages(db_session, client, monkeypatch):
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    cid = "history-test-conv"
    client.post("/qa", json={"query": "Cuánto fue la inflación", "conversation_id": cid})

    history_resp = client.get(f"/qa/history?conversation_id={cid}")
    assert history_resp.status_code == 200
    msgs = history_resp.json()
    assert len(msgs) == 2  # user + assistant
    roles = [m["role"] for m in msgs]
    assert "user" in roles
    assert "assistant" in roles


@pytest.mark.asyncio
async def test_qa_conversation_history_is_passed_to_synthesis(db_session, client, monkeypatch):
    """Second Q&A in same conversation must include prior history."""
    await _seed_article(db_session)
    fake_client = _make_fake_openai()
    monkeypatch.setattr("noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client)

    cid = "multi-turn-conv"

    # First turn
    r1 = client.post("/qa", json={"query": "Cuánto fue la inflación", "conversation_id": cid})
    assert r1.status_code == 200

    # Reset mock call count to inspect the second call only
    fake_client.chat.completions.create.reset_mock()

    # Second turn
    r2 = client.post("/qa", json={"query": "Y el mes pasado?", "conversation_id": cid})
    assert r2.status_code == 200

    # The synthesis call for the second turn should include history messages
    # (at minimum 2 prior messages: user + assistant from turn 1)
    # The messages arg is the first positional-or-kw argument
    all_calls = fake_client.chat.completions.create.call_args_list
    # Find the synthesis call — it will have messages with history
    synthesis_messages = None
    for call in all_calls:
        messages = call.kwargs.get("messages") or (call.args[0] if call.args else None)
        if messages and any(m.get("role") == "assistant" for m in messages):
            synthesis_messages = messages
            break

    assert synthesis_messages is not None, "Synthesis call with history not found"


def test_qa_rejects_short_query(client):
    r = client.post("/qa", json={"query": "x"})
    assert r.status_code == 422


def test_qa_rejects_long_query(client):
    r = client.post("/qa", json={"query": "x" * 600})
    assert r.status_code == 422


def test_qa_rejects_conversation_id_too_long(client):
    r = client.post("/qa", json={"query": "valid query here", "conversation_id": "x" * 65})
    assert r.status_code == 422
