import os

import pytest

from noticias_api.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CRON_HOUR", "8")
    monkeypatch.setenv("TOP_N_CLUSTERS", "20")
    monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.80")

    s = Settings()

    assert s.database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert s.openai_api_key == "sk-test"
    assert s.cron_hour == 8
    assert s.top_n_clusters == 20
    assert s.similarity_threshold == 0.80


def test_settings_has_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    s = Settings()

    assert s.cron_hour == 7
    assert s.cron_minute == 0
    assert s.top_n_clusters == 15
    assert s.similarity_threshold == 0.78
    assert s.log_level == "INFO"
