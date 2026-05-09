from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from noticias_api.db.models import Run


def test_post_refresh_returns_202_with_run_id(client, monkeypatch):
    async def fake_run_locked(trigger, settings):
        return 42

    monkeypatch.setattr(
        "noticias_api.api.runs._run_locked", fake_run_locked
    )
    monkeypatch.setattr(
        "noticias_api.api.runs.is_pipeline_running", lambda: False
    )

    response = client.post("/refresh")
    assert response.status_code == 202
    assert "run_id" in response.json()
    assert response.json()["status"] == "queued"


def test_post_refresh_returns_409_when_already_running(client, monkeypatch):
    monkeypatch.setattr("noticias_api.api.runs.is_pipeline_running", lambda: True)
    monkeypatch.setattr("noticias_api.api.runs.get_current_run_id", lambda: 99)

    response = client.post("/refresh")
    assert response.status_code == 409
    assert response.json()["detail"]["run_id"] == 99


@pytest.mark.asyncio
async def test_get_run_returns_status(db_session, client):
    run = Run(trigger="manual", status="success")
    db_session.add(run)
    await db_session.commit()

    response = client.get(f"/runs/{run.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run.id
    assert body["status"] == "success"


def test_get_run_404(client):
    response = client.get("/runs/999999")
    assert response.status_code == 404
