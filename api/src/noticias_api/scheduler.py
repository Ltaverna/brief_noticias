import asyncio
import logging
from datetime import UTC, date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI

from noticias_api.config import Settings
from noticias_api.db.session import async_session_factory
from noticias_api.notifiers.digest import send_digest
from noticias_api.pipeline.runner import PipelineConfig, run_pipeline

logger = logging.getLogger(__name__)

_pipeline_lock = asyncio.Lock()
_current_run_id: int | None = None


def get_current_run_id() -> int | None:
    return _current_run_id


async def _run_locked(trigger: str, settings: Settings) -> int:
    global _current_run_id
    async with _pipeline_lock:
        cfg = PipelineConfig(
            top_n=settings.top_n_clusters,
            similarity_threshold=settings.similarity_threshold,
            window_hours=settings.cluster_window_hours,
            embedding_model=settings.embedding_model,
            analysis_model=settings.chat_model_analysis,
            user_agent=settings.user_agent,
            max_concurrent=settings.max_concurrent_fetches,
            merge_threshold=settings.merge_threshold,
            merge_window_hours=settings.merge_window_hours,
            saga_threshold=settings.saga_threshold,
            saga_window_hours=settings.saga_window_hours,
        )
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        async with async_session_factory() as session:
            run_id = await run_pipeline(
                session, cfg, trigger=trigger, openai_client=client
            )
            _current_run_id = run_id
            try:
                await send_digest(session, settings, date.today())
            except Exception:
                logger.exception("digest send failed (non-fatal)")
            return run_id


def schedule_pipeline_in_task(trigger: str, settings: Settings) -> asyncio.Task:
    return asyncio.create_task(_run_locked(trigger, settings))


def setup_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(
        lambda: asyncio.create_task(_run_locked("cron", settings)),
        CronTrigger(hour=settings.cron_hour, minute=settings.cron_minute),
        id="daily_briefing",
        replace_existing=True,
    )
    return scheduler


def is_pipeline_running() -> bool:
    return _pipeline_lock.locked()
