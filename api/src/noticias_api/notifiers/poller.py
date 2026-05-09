import asyncio
import logging

from noticias_api.config import Settings
from noticias_api.db.session import async_session_factory
from noticias_api.notifiers.bot_handler import handle_update
from noticias_api.notifiers.telegram import TelegramClient, TelegramError

logger = logging.getLogger(__name__)


async def run_poller(settings: Settings, *, stop_event: asyncio.Event) -> None:
    """Long-poll Telegram getUpdates and dispatch each update to handle_update.

    Exits cleanly when stop_event is set or the task is cancelled.
    """
    if not settings.telegram_bot_token:
        logger.warning("polling enabled but no bot token; exiting")
        return
    bot = TelegramClient(settings.telegram_bot_token)
    offset: int | None = None
    backoff = 1.0
    while not stop_event.is_set():
        try:
            updates = await bot.get_updates(offset=offset, timeout=25)
            backoff = 1.0
            for upd in updates:
                offset = max(offset or 0, upd.get("update_id", 0)) + 1
                async with async_session_factory() as session:
                    try:
                        await handle_update(upd, settings=settings, session=session)
                    except Exception:
                        logger.exception("poll update handler failed for update %s", upd.get("update_id"))
        except asyncio.CancelledError:
            logger.info("poller task cancelled")
            return
        except TelegramError as exc:
            logger.warning("poller telegram error: %s", exc)
            await asyncio.sleep(min(60.0, backoff))
            backoff = min(60.0, backoff * 2)
        except Exception:
            logger.exception("poller loop error")
            await asyncio.sleep(min(60.0, backoff))
            backoff = min(60.0, backoff * 2)
