from datetime import UTC, datetime, timedelta

import pytest

from noticias_api.db.models import (
    Analysis,
    Cluster,
    ClusterEntity,
    Entity,
    Source,
)


async def _seed(db_session):
    """Seed two sources, one cluster, one analysis, one entity linked to it."""
    for slug in ("la-nacion", "pagina-12"):
        s = Source(
            slug=slug, name=slug.upper(), editorial_group="mainstream",
            rss_url="x", base_url="x",
        )
        db_session.add(s)
    await db_session.commit()

    now = datetime.now(UTC)
    cluster = Cluster(article_count=2, source_count=2, last_seen_at=now, first_seen_at=now)
    db_session.add(cluster)
    await db_session.commit()

    db_session.add(Analysis(
        cluster_id=cluster.id,
        headline="Adorni en problemas",
        common_facts=[],
        by_source={
            "la-nacion": {"highlights": [], "framing": "x", "tone": "favorable"},
            "pagina-12": {"highlights": [], "framing": "x", "tone": "crítico"},
        },
        omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v2",
    ))

    ent = Entity(name="Manuel Adorni", kind="person", canonical="manuel adorni")
    db_session.add(ent)
    await db_session.commit()

    db_session.add(ClusterEntity(cluster_id=cluster.id, entity_id=ent.id))
    await db_session.commit()
    return cluster.id


def test_tone_trends_empty_when_no_data(client):
    r = client.get("/analytics/tone-trends")
    assert r.status_code == 200
    body = r.json()
    assert body["buckets"] == []
    assert body["sources"] == []


@pytest.mark.asyncio
async def test_tone_trends_aggregates_by_source(db_session, client):
    await _seed(db_session)
    r = client.get("/analytics/tone-trends?bucket=day")
    assert r.status_code == 200
    body = r.json()
    assert "la-nacion" in body["sources"]
    assert "pagina-12" in body["sources"]
    # Check la-nacion has a 'favorable' count
    ln_data = body["data"]["la-nacion"]
    bucket = list(ln_data.keys())[0]
    assert ln_data[bucket].get("favorable", 0) == 1


@pytest.mark.asyncio
async def test_tone_trends_normalizes_accented_tone(db_session, client):
    """'crítico' (with accent) must normalize to 'critico' in the TONES list."""
    await _seed(db_session)
    r = client.get("/analytics/tone-trends?bucket=day")
    body = r.json()
    p12_data = body["data"]["pagina-12"]
    bucket = list(p12_data.keys())[0]
    # 'crítico' → normalized to 'critico'
    assert p12_data[bucket].get("critico", 0) == 1


@pytest.mark.asyncio
async def test_tone_trends_filters_by_entity(db_session, client):
    await _seed(db_session)
    r = client.get("/analytics/tone-trends?entity=manuel adorni&bucket=day")
    assert r.status_code == 200
    body = r.json()
    assert "la-nacion" in body["sources"]


@pytest.mark.asyncio
async def test_tone_trends_unknown_entity_returns_empty(db_session, client):
    await _seed(db_session)
    r = client.get("/analytics/tone-trends?entity=ramirez&bucket=day")
    assert r.json()["sources"] == []


def test_bias_scorecard_empty(client):
    r = client.get("/analytics/bias-scorecard")
    assert r.status_code == 200
    body = r.json()
    assert body["entities"] == []
    assert body["rows"] == []


@pytest.mark.asyncio
async def test_bias_scorecard_returns_rows(db_session, client):
    await _seed(db_session)
    r = client.get("/analytics/bias-scorecard?top_entities=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["entities"]) >= 1
    assert any(row["source"] == "la-nacion" for row in body["rows"])
    # The la-nacion row should have a 'favorable' count for manuel adorni
    ln_row = next(row for row in body["rows"] if row["source"] == "la-nacion")
    cell = ln_row["cells"]["manuel adorni"]
    assert cell["favorable"] == 1
    assert cell["total"] == 1


@pytest.mark.asyncio
async def test_bias_scorecard_pagina12_critico(db_session, client):
    """pagina-12 uses 'crítico' (accented) — should map to critico bucket."""
    await _seed(db_session)
    r = client.get("/analytics/bias-scorecard?top_entities=2")
    body = r.json()
    p12_row = next((row for row in body["rows"] if row["source"] == "pagina-12"), None)
    assert p12_row is not None
    cell = p12_row["cells"]["manuel adorni"]
    assert cell["critico"] == 1
    assert cell["total"] == 1


@pytest.mark.asyncio
async def test_tone_trends_week_bucket(db_session, client):
    """With bucket=week the bucket key is the Monday of the current week."""
    await _seed(db_session)
    r = client.get("/analytics/tone-trends?bucket=week")
    assert r.status_code == 200
    body = r.json()
    assert len(body["buckets"]) >= 1
    # Bucket keys must be YYYY-MM-DD format (Monday)
    for bk in body["buckets"]:
        parts = bk.split("-")
        assert len(parts) == 3
