import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from noticias_api.db.models import (
    Analysis,
    Cluster,
    ClusterEntity,
    Entity,
    Source,
)
from noticias_api.pipeline.entities import (
    EntityExtractionResult,
    canonicalize,
    extract_entities,
    extract_for_top_clusters,
    persist_entities,
)


def test_canonicalize_lowercases_and_strips():
    assert canonicalize("Manuel Adorni") == "manuel adorni"
    assert canonicalize("¡Casa Rosada!") == "casa rosada"
    assert canonicalize("  Banco   Central  ") == "banco central"


def _mock_response(content):
    r = MagicMock()
    r.choices = [MagicMock(message=MagicMock(content=content))]
    return r


@pytest.mark.asyncio
async def test_extract_entities_parses_json():
    payload = {
        "persons": ["Manuel Adorni", "Patricia Bullrich"],
        "orgs": ["Gobierno"],
        "places": ["Casa Rosada"],
        "events": ["Adornigate"],
    }
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    result = await extract_entities(
        client, headline="x", common_facts=["a", "b"], model="gpt-4o-mini"
    )
    assert result is not None
    assert "Manuel Adorni" in result.persons
    assert "Adornigate" in result.events


@pytest.mark.asyncio
async def test_extract_entities_returns_none_after_failures():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response("not json")
    )
    result = await extract_entities(
        client, headline="x", common_facts=[], model="gpt-4o-mini"
    )
    assert result is None


@pytest.mark.asyncio
async def test_persist_entities_creates_rows(db_session):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    cluster = Cluster(article_count=1, source_count=1,
                      last_seen_at=datetime.now(UTC))
    db_session.add(cluster)
    await db_session.commit()

    extraction = EntityExtractionResult(
        persons=["Manuel Adorni"], orgs=["Gobierno"],
        places=["Casa Rosada"], events=[],
    )
    n = await persist_entities(db_session, cluster.id, extraction)
    assert n == 3

    ents = (await db_session.scalars(select(Entity))).all()
    kinds = {e.kind for e in ents}
    assert kinds == {"person", "org", "place"}

    links = (await db_session.scalars(select(ClusterEntity))).all()
    assert len(links) == 3


@pytest.mark.asyncio
async def test_persist_entities_dedupes_canonical_across_clusters(db_session):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    c1 = Cluster(article_count=1, source_count=1,
                 last_seen_at=datetime.now(UTC))
    c2 = Cluster(article_count=1, source_count=1,
                 last_seen_at=datetime.now(UTC))
    db_session.add_all([c1, c2])
    await db_session.commit()

    e1 = EntityExtractionResult(persons=["Adorni"])
    e2 = EntityExtractionResult(persons=["Manuel Adorni"])
    await persist_entities(db_session, c1.id, e1)
    await persist_entities(db_session, c2.id, e2)

    persons = (
        await db_session.scalars(select(Entity).where(Entity.kind == "person"))
    ).all()
    # Two different display names but two different canonical keys: "adorni" vs "manuel adorni".
    # That's expected — the LLM should be instructed to use full names; if it doesn't,
    # we'd see two entities here. This test documents the current canonicalization behavior.
    assert len(persons) == 2


@pytest.mark.asyncio
async def test_persist_entities_replaces_links_on_re_run(db_session):
    """Re-running entity extraction for a cluster removes old associations
    before creating new ones, so re-extraction is authoritative."""
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    c = Cluster(article_count=1, source_count=1,
                last_seen_at=datetime.now(UTC))
    db_session.add(c)
    await db_session.commit()

    await persist_entities(db_session, c.id,
                           EntityExtractionResult(persons=["Adorni", "Bullrich"]))
    await persist_entities(db_session, c.id,
                           EntityExtractionResult(persons=["Bullrich", "Caputo"]))

    links = (await db_session.scalars(
        select(ClusterEntity).where(ClusterEntity.cluster_id == c.id)
    )).all()
    assert len(links) == 2  # only Bullrich + Caputo

    # All three Entity rows should exist (Adorni stays around but unlinked)
    persons = (
        await db_session.scalars(select(Entity).where(Entity.kind == "person"))
    ).all()
    assert len(persons) == 3


@pytest.mark.asyncio
async def test_extract_for_top_clusters_skips_if_already_extracted(db_session, monkeypatch):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    c = Cluster(article_count=1, source_count=1, is_top=True,
                last_seen_at=datetime.now(UTC))
    db_session.add(c)
    await db_session.commit()
    db_session.add(Analysis(
        cluster_id=c.id, headline="Test",
        common_facts=["x"], by_source={}, omissions=[], divergences=[],
        model="x", prompt_version="v2",
    ))
    await db_session.commit()

    # Pre-link an entity to mark this cluster "already extracted"
    ent = Entity(name="X", kind="person", canonical="x")
    db_session.add(ent)
    await db_session.commit()
    db_session.add(ClusterEntity(cluster_id=c.id, entity_id=ent.id))
    await db_session.commit()

    client = MagicMock()
    client.chat.completions.create = AsyncMock()  # should NOT be called

    stats = await extract_for_top_clusters(
        db_session, client, model="gpt-4o-mini"
    )
    assert stats["clusters_extracted"] == 0
    assert stats["clusters_skipped"] == 1
    client.chat.completions.create.assert_not_called()
