"""Tests for Telegram admin endpoints."""
import httpx
import pytest


def test_setup_webhook_calls_telegram_api(client, monkeypatch, respx_mock):
    """POST /telegram/setup-webhook should call Telegram's setWebhook."""
    respx_mock.post("https://api.telegram.org/bot:ABC/setWebhook").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_bot_token", ":ABC")
    object.__setattr__(s, "telegram_webhook_secret", None)

    response = client.post(
        "/telegram/setup-webhook",
        json={"url": "https://example.com/telegram/webhook", "drop_pending": False},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_clear_webhook_calls_telegram_api(client, monkeypatch, respx_mock):
    """POST /telegram/clear-webhook should call Telegram's deleteWebhook."""
    respx_mock.post("https://api.telegram.org/bot:ABC/deleteWebhook").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_bot_token", ":ABC")

    response = client.post("/telegram/clear-webhook")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_setup_webhook_no_token_returns_400(client, monkeypatch):
    """Setup webhook without token returns 400."""
    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_bot_token", None)

    response = client.post(
        "/telegram/setup-webhook",
        json={"url": "https://example.com/telegram/webhook"},
    )
    assert response.status_code == 400


def test_clear_webhook_no_token_returns_400(client, monkeypatch):
    """Clear webhook without token returns 400."""
    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_bot_token", None)

    response = client.post("/telegram/clear-webhook")
    assert response.status_code == 400


def test_info_endpoint_returns_mode(client, monkeypatch, respx_mock):
    """GET /telegram/info returns bot_mode and webhook_info."""
    respx_mock.get("https://api.telegram.org/bot:ABC/getWebhookInfo").mock(
        return_value=httpx.Response(
            200, json={"ok": True, "result": {"url": "", "pending_update_count": 0}}
        )
    )

    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_bot_token", ":ABC")
    object.__setattr__(s, "telegram_bot_mode", "polling")

    response = client.get("/telegram/info")
    assert response.status_code == 200
    data = response.json()
    assert "bot_mode" in data
    assert "webhook_info" in data
    assert "allowed_chats" in data
