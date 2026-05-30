import asyncio
import logging
from datetime import UTC, date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI

from noticias_api.config import Settings
from noticias_api.db.session import async_session_factory
from noticias_api.notifiers.alerts import detect_and_send_alerts
from noticias_api.notifiers.digest import send_digest
from noticias_api.pipeline.runner import PipelineConfig, run_pipeline

logger = logging.getLogger(__name__)

# Module-level singletons for the polling background task
_poller_task: asyncio.Task | None = None
_poller_stop: asyncio.Event | None = None

_pipeline_lock = asyncio.Lock()
_current_run_id: int | None = None
_loop: asyncio.AbstractEventLoop | None = None


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
            enable_entity_extraction=settings.enable_entity_extraction,
            entity_extraction_model=settings.entity_extraction_model,
            enable_topic_classification=settings.enable_topic_classification,
            topic_classification_model=settings.topic_classification_model,
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
            try:
                await detect_and_send_alerts(session, settings)
            except Exception:
                logger.exception("alert detection failed (non-fatal)")
            return run_id


def schedule_pipeline_in_task(trigger: str, settings: Settings) -> asyncio.Task:
    return asyncio.create_task(_run_locked(trigger, settings))


def _schedule_pipeline(trigger: str, settings: Settings) -> None:
    """Thread-safe wrapper to schedule the pipeline coroutine in the main event loop."""
    global _loop
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_run_locked(trigger, settings), _loop)
    else:
        logger.error("No event loop available for scheduler job")


def setup_scheduler(settings: Settings) -> AsyncIOScheduler:
    global _poller_task, _poller_stop, _loop
    _loop = asyncio.get_event_loop()
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    for hour in settings.cron_hours_list:
        scheduler.add_job(
            _schedule_pipeline,
            CronTrigger(hour=hour, minute=settings.cron_minute),
            args=("cron", settings),
            id=f"daily_briefing_{hour:02d}",
            replace_existing=True,
        )

    # Start telegram poller if mode=polling — requires a running event loop.
    # When called outside one (e.g. unit tests), skip silently; the FastAPI
    # lifespan ensures a loop is running in production.
    if settings.telegram_bot_mode == "polling" and settings.enable_telegram:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("setup_scheduler: no running event loop, skipping poller start")
        else:
            from noticias_api.notifiers.poller import run_poller  # avoid circular import at module level

            _poller_stop = asyncio.Event()
            _poller_task = asyncio.create_task(run_poller(settings, stop_event=_poller_stop))
            logger.info("Telegram polling task started")

    return scheduler


def teardown_polling() -> None:
    """Signal the polling task to stop and cancel it."""
    global _poller_task, _poller_stop
    if _poller_stop:
        _poller_stop.set()
    if _poller_task:
        _poller_task.cancel()
    _poller_stop = None
    _poller_task = None


def is_pipeline_running() -> bool:
    return _pipeline_lock.locked()
