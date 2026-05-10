from datetime import UTC, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source


@pytest.mark.asyncio
async def test_regenerate_replaces_analysis(db_session, client, monkeypatch):
    src = Source(
        slug="ln", name="LN", editorial_group="mainstream",
        rss_url="x", base_url="x",
    )
    db_session.add(src)
    await db_session.commit()

    cluster = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(cluster)
    await db_session.commit()

    db_session.add(Article(
        source_id=src.id, external_id="a1", url="https://x/a1",
        title="title", content="content",
        published_at=datetime.now(UTC), cluster_id=cluster.id,
    ))
    db_session.add(Analysis(
        cluster_id=cluster.id, headline="OLD",
        common_facts=[], by_source={}, omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v1",
    ))
    await db_session.commit()

    # Mock the analyze step: substitute _analyze_top_clusters
    async def fake_analyze(session, client, cfg, *, only_cluster_ids=None):
        from noticias_api.db.models import Analysis as A
        for cid in (only_cluster_ids or set()):
            session.add(A(
                cluster_id=cid, headline="NEW",
                common_facts=["f"], by_source={}, omissions=[], divergences=[],
                model="gpt-4o", prompt_version="v2",
            ))
        await session.commit()
        return {"analyzed": len(only_cluster_ids or set())}

    monkeypatch.setattr(
        "noticias_api.api.clusters._analyze_top_clusters", fake_analyze
    )

    resp = client.post(f"/clusters/{cluster.id}/regenerate-analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["headline"] == "NEW"
    assert body["prompt_version"] == "v2"


@pytest.mark.asyncio
async def test_regenerate_404_for_unknown_cluster(client):
    resp = client.post("/clusters/999999/regenerate-analysis")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_returns_502_when_analysis_fails(db_session, client, monkeypatch):
    src = Source(
        slug="ln2", name="LN2", editorial_group="mainstream",
        rss_url="x2", base_url="x2",
    )
    db_session.add(src)
    await db_session.commit()

    cluster = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(cluster)
    await db_session.commit()

    db_session.add(Article(
        source_id=src.id, external_id="a2", url="https://x/a2",
        title="t", published_at=datetime.now(UTC), cluster_id=cluster.id,
    ))
    await db_session.commit()

    async def fake_analyze_noop(session, client, cfg, *, only_cluster_ids=None):
        return {"analyzed": 0}

    monkeypatch.setattr(
        "noticias_api.api.clusters._analyze_top_clusters", fake_analyze_noop
    )

    resp = client.post(f"/clusters/{cluster.id}/regenerate-analysis")
    assert resp.status_code == 502
