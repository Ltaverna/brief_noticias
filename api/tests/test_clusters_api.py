from datetime import UTC, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source


@pytest.mark.asyncio
async def test_get_cluster_returns_full_detail(db_session, client):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    cluster = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(cluster)
    await db_session.commit()

    art = Article(
        source_id=src.id, external_id="a1", url="https://ln/a1",
        title="Inflación abril", summary="resumen", content="contenido completo",
        has_full_text=True, published_at=datetime.now(UTC), cluster_id=cluster.id,
    )
    db_session.add(art)

    db_session.add(Analysis(
        cluster_id=cluster.id, headline="Inflación abril 4,2%",
        common_facts=["IPC 4,2%"],
        by_source={"ln": {"highlights": ["x"], "framing": "y", "tone": "neutral"}},
        omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v1",
    ))
    await db_session.commit()

    response = client.get(f"/clusters/{cluster.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == cluster.id
    assert body["analysis"]["headline"] == "Inflación abril 4,2%"
    assert len(body["articles"]) == 1
    assert body["articles"][0]["source"]["slug"] == "ln"


def test_get_cluster_404(client):
    response = client.get("/clusters/999999")
    assert response.status_code == 404
