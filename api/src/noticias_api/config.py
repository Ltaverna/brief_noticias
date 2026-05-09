from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str
    openai_api_key: str

    log_level: str = "INFO"
    cron_hour: int = 7
    cron_minute: int = 0
    top_n_clusters: int = 15
    similarity_threshold: float = 0.78
    cluster_window_hours: int = 48
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chat_model_analysis: str = "gpt-4o"
    user_agent: str = "noticias-bot/0.1 (+https://github.com/personal/noticias)"
    max_concurrent_fetches: int = 8


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
