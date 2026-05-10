from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.db.models import Article, Cluster, Source
from noticias_api.qa.retrieval import retrieve_chunks


@pytest.mark.asyncio
async def test_retrieve_returns_chunks_ordered_by_similarity(db_session):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    cluster = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add(cluster)
    await db_session.commit()

    near = [1.0] + [0.0] * 1535
    far = [0.0] * 1535 + [1.0]
    db_session.add_all([
        Article(source_id=src.id, external_id="a1", url="https://x/a1",
                title="cerca", content="x", embedding=near,
                published_at=now, cluster_id=cluster.id),
        Article(source_id=src.id, external_id="a2", url="https://x/a2",
                title="lejos", content="y", embedding=far,
                published_at=now, cluster_id=cluster.id),
    ])
    await db_session.commit()

    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.data = [MagicMock(embedding=near)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_response)

    chunks = await retrieve_chunks(
        db_session, fake_client, query="x",
        embedding_model="text-embedding-3-large", top_k=10,
    )
    assert len(chunks) == 2
    # Closest to query (which has the "near" vector) should come first.
    assert chunks[0].title == "cerca"


@pytest.mark.asyncio
async def test_retrieve_skips_articles_without_embedding(db_session):
    src = Source(slug="ln2", name="LN2", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    db_session.add(Article(
        source_id=src.id, external_id="a1", url="u1", title="no embedding",
        content="z", embedding=None, published_at=now,
    ))
    db_session.add(Article(
        source_id=src.id, external_id="a2", url="u2", title="has embedding",
        content="z", embedding=[1.0] + [0.0]*1535, published_at=now,
    ))
    await db_session.commit()

    fake = MagicMock()
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(embedding=[1.0] + [0.0]*1535)]
    fake.embeddings.create = AsyncMock(return_value=fake_resp)

    chunks = await retrieve_chunks(
        db_session, fake, query="x",
        embedding_model="text-embedding-3-large", top_k=10,
    )
    assert len(chunks) == 1
    assert chunks[0].title == "has embedding"
