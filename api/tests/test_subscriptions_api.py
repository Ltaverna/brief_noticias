"""Tests for subscriptions REST API (D6)."""
import pytest
from fastapi.testclient import TestClient

from noticias_api.config import Settings, get_settings
from noticias_api.main import app


# ---------------------------------------------------------------------------
# Helper: override FastAPI DI settings
# ---------------------------------------------------------------------------

def _make_settings(chat_id: str | None = "999") -> Settings:
    return Settings(
        database_url="postgresql+psycopg://x:x@h:5432/d",
        openai_api_key="sk-x",
        telegram_bot_token=":ABC",
        telegram_chat_id=chat_id,
        enable_telegram=True,
        public_base_url="http://localhost:3000",
    )


def _override_settings(settings: Settings):
    """Return a factory that replaces the get_settings DI dependency."""
    return lambda: settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_entity_subscription(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.post(
            "/subscriptions",
            json={"kind": "entity", "value": "Manuel Adorni"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["kind"] == "entity"
        assert data["value"] == "manuel adorni"   # lowercased + stripped
        assert data["channel"] == "telegram"
        assert data["chat_id"] == "999"
        assert data["alert_threshold_sources"] is None
        assert "id" in data
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_create_subscription_with_alert_threshold(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.post(
            "/subscriptions",
            json={"kind": "entity", "value": "adorni", "alert_threshold_sources": 3},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["alert_threshold_sources"] == 3
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_create_all_subscription(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.post("/subscriptions", json={"kind": "all"})
        assert resp.status_code == 201, resp.text
        assert resp.json()["kind"] == "all"
        assert resp.json()["value"] is None
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_create_entity_sub_requires_value(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.post("/subscriptions", json={"kind": "entity"})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_subscriptions(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        # Create two subscriptions
        client.post("/subscriptions", json={"kind": "entity", "value": "adorni"})
        client.post("/subscriptions", json={"kind": "entity", "value": "milei"})

        resp = client.get("/subscriptions")
        assert resp.status_code == 200
        data = resp.json()
        values = [s["value"] for s in data]
        assert "adorni" in values
        assert "milei" in values
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_delete_subscription(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        create_resp = client.post(
            "/subscriptions", json={"kind": "entity", "value": "adorni"}
        )
        sub_id = create_resp.json()["id"]

        del_resp = client.delete(f"/subscriptions/{sub_id}")
        assert del_resp.status_code == 204

        list_resp = client.get("/subscriptions")
        ids = [s["id"] for s in list_resp.json()]
        assert sub_id not in ids
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_delete_nonexistent_subscription(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.delete("/subscriptions/99999")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_returns_empty_when_none(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.get("/subscriptions")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_chat_id_not_configured_returns_400(client: TestClient):
    """Without telegram_chat_id configured, endpoints return 400."""
    settings = _make_settings(chat_id=None)
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.get("/subscriptions")
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_invalid_kind_rejected(client: TestClient):
    settings = _make_settings()
    app.dependency_overrides[get_settings] = _override_settings(settings)
    try:
        resp = client.post("/subscriptions", json={"kind": "bad_kind", "value": "x"})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_settings, None)
