from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from noticias_api.db.models import Cluster, ClusterNote


@pytest.mark.asyncio
async def test_add_and_list_notes(db_session, client):
    c = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(c)
    await db_session.commit()

    r = client.post(f"/clusters/{c.id}/notes", json={"note": "primer apunte"})
    assert r.status_code == 201
    body = r.json()
    assert body["note"] == "primer apunte"
    note_id = body["id"]

    r2 = client.get(f"/clusters/{c.id}/notes")
    assert r2.status_code == 200
    assert any(n["id"] == note_id for n in r2.json())


def test_add_note_404_for_unknown_cluster(client):
    r = client.post("/clusters/999999/notes", json={"note": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_note(db_session, client):
    c = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(c)
    await db_session.commit()
    note = ClusterNote(cluster_id=c.id, note="x")
    db_session.add(note)
    await db_session.commit()

    r = client.delete(f"/notes/{note.id}")
    assert r.status_code == 204

    rows = (await db_session.scalars(select(ClusterNote))).all()
    assert rows == []


def test_validate_min_length(client):
    r = client.post("/clusters/1/notes", json={"note": ""})
    assert r.status_code == 422
