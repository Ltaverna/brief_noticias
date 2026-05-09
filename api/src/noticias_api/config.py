from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str
    openai_api_key: str

    log_level: str = "INFO"
    cron_hour: int = 7
    cron_minute: int = 0
    top_n_clusters: int = 20
    similarity_threshold: float = 0.70
    cluster_window_hours: int = 48
    embedding_model: str = "text-embedding-3-large"
    chat_model: str = "gpt-4o-mini"
    chat_model_analysis: str = "gpt-4o"
    user_agent: str = "noticias-bot/0.1 (+https://github.com/personal/noticias)"
    max_concurrent_fetches: int = 8
    merge_threshold: float = 0.85
    merge_window_hours: int = 72
    saga_threshold: float = 0.78
    saga_window_hours: int = 168

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    enable_telegram: bool = False
    public_base_url: str = "http://localhost:3000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
