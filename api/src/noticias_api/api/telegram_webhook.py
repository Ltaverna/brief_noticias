import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.session import async_session_factory
from noticias_api.notifiers.bot_handler import handle_update

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook", status_code=200)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    """Receive a Telegram Update via webhook.

    Verifies the secret token when configured, then dispatches processing
    in a background task so Telegram gets a fast 200 OK.
    """
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(403, "invalid secret token")
    update = await request.json()
    # Fire-and-forget — ack to Telegram immediately
    asyncio.create_task(_process(update, settings))
    return {"ok": True}


async def _process(update: dict, settings: Settings) -> None:
    try:
        async with async_session_factory() as session:
            await handle_update(update, settings=settings, session=session)
    except Exception:
        logger.exception("webhook update processing failed for update %s", update.get("update_id"))
