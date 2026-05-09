from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.db.models import Article, Cluster, Source


@pytest.mark.asyncio
async def test_qa_returns_answer_with_citations(db_session, client, monkeypatch):
    # Seed articles with embeddings
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
        embedding=[1.0] + [0.0]*1535,
        published_at=now, cluster_id=cluster.id,
    ))
    await db_session.commit()

    # Patch OpenAI calls.
    fake_client = MagicMock()
    fake_emb = MagicMock()
    fake_emb.data = [MagicMock(embedding=[1.0] + [0.0]*1535)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_emb)
    fake_chat = MagicMock()
    fake_chat.choices = [
        MagicMock(message=MagicMock(content="Según el INDEC, fue del 4,2% [1]."))
    ]
    fake_client.chat.completions.create = AsyncMock(return_value=fake_chat)

    monkeypatch.setattr(
        "noticias_api.api.qa.AsyncOpenAI", lambda **kw: fake_client
    )

    response = client.post("/qa", json={"query": "Cuánto fue la inflación"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Cuánto fue la inflación"
    assert "[1]" in body["answer"]
    assert body["used_citations"] == [1]
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source_slug"] == "ln"


def test_qa_rejects_short_query(client):
    r = client.post("/qa", json={"query": "x"})
    assert r.status_code == 422


def test_qa_rejects_long_query(client):
    r = client.post("/qa", json={"query": "x" * 600})
    assert r.status_code == 422
