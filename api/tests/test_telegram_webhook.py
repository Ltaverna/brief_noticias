"""Tests for POST /telegram/webhook."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest


def test_webhook_no_secret_returns_ok(client, monkeypatch):
    """With no secret configured, any valid JSON body should return 200 ok."""
    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_webhook_secret", None)

    # Patch _process so we don't actually attempt to call Telegram
    async def fake_process(update, settings):
        pass

    monkeypatch.setattr(
        "noticias_api.api.telegram_webhook._process", fake_process
    )

    response = client.post("/telegram/webhook", json={"update_id": 1})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    """When a secret is configured, a missing/wrong header → 403."""
    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_webhook_secret", "topsecret")

    # Do NOT send the secret header
    response = client.post("/telegram/webhook", json={"update_id": 1})
    assert response.status_code == 403


def test_webhook_accepts_correct_secret(client, monkeypatch):
    """Correct secret token header → 200."""
    from noticias_api.config import get_settings

    s = get_settings()
    object.__setattr__(s, "telegram_webhook_secret", "topsecret")

    async def fake_process(update, settings):
        pass

    monkeypatch.setattr(
        "noticias_api.api.telegram_webhook._process", fake_process
    )

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "topsecret"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
