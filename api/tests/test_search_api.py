from datetime import UTC, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source


@pytest.fixture
async def seeded(db_session):
    src = Source(
        slug="ln",
        name="LN",
        editorial_group="mainstream",
        rss_url="x",
        base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    cluster = Cluster(article_count=2, source_count=1, last_seen_at=now)
    db_session.add(cluster)
    await db_session.commit()

    db_session.add_all(
        [
            Article(
                source_id=src.id,
                external_id="a1",
                url="https://x/a1",
                title="Inflación de abril fue del 4,2%",
                content="El INDEC informó que la inflación acumulada fue alta.",
                published_at=now,
                cluster_id=cluster.id,
            ),
            Article(
                source_id=src.id,
                external_id="a2",
                url="https://x/a2",
                title="Boca venció a River por 2-1",
                content="El partido se jugó en La Bombonera",
                published_at=now,
                cluster_id=cluster.id,
            ),
        ]
    )
    db_session.add(
        Analysis(
            cluster_id=cluster.id,
            headline="INDEC publicó la inflación de abril",
            common_facts=["IPC 4,2%", "acumulada 142%"],
            by_source={},
            omissions=[],
            divergences=[],
            model="gpt-4o",
            prompt_version="v2",
        )
    )
    await db_session.commit()
    return cluster.id


def test_search_requires_query(client):
    r = client.get("/search")
    assert r.status_code == 422


def test_search_short_query_rejected(client):
    r = client.get("/search?q=a")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_finds_article_by_title(seeded, client):
    r = client.get("/search?q=inflación")
    assert r.status_code == 200
    body = r.json()
    assert any("inflaci" in h["title"].lower() for h in body["articles"])


@pytest.mark.asyncio
async def test_search_finds_cluster_by_analysis(seeded, client):
    cluster_id = seeded
    r = client.get("/search?q=INDEC")
    assert r.status_code == 200
    body = r.json()
    cluster_ids = {c["id"] for c in body["clusters"]}
    assert cluster_id in cluster_ids


@pytest.mark.asyncio
async def test_search_returns_empty_on_unknown_term(seeded, client):
    r = client.get("/search?q=xyzunknownterm")
    assert r.status_code == 200
    body = r.json()
    assert body["clusters"] == []
    assert body["articles"] == []


@pytest.mark.asyncio
async def test_search_uses_spanish_stemming(seeded, client):
    """Spanish FTS should handle stemming — endpoint must return valid shape."""
    r = client.get("/search?q=inflaciones")
    assert r.status_code == 200
    body = r.json()
    assert "articles" in body and "clusters" in body


@pytest.mark.asyncio
async def test_search_result_shape(seeded, client):
    """Verify response JSON has expected top-level keys and types."""
    r = client.get("/search?q=inflación")
    assert r.status_code == 200
    body = r.json()
    assert "query" in body
    assert body["query"] == "inflación"
    assert isinstance(body["clusters"], list)
    assert isinstance(body["articles"], list)
