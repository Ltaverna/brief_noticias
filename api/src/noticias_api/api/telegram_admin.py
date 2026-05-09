from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from noticias_api.config import Settings, get_settings
from noticias_api.notifiers.bot_handler import allowed_chats
from noticias_api.notifiers.telegram import TelegramClient, TelegramError

router = APIRouter(tags=["telegram-admin"])


class WebhookSetup(BaseModel):
    url: str  # e.g. https://your-domain.example.com/telegram/webhook
    drop_pending: bool = False


@router.post("/telegram/setup-webhook")
async def setup_webhook(
    body: WebhookSetup,
    settings: Settings = Depends(get_settings),
):
    """Register a webhook URL with Telegram."""
    if not settings.telegram_bot_token:
        raise HTTPException(400, "no telegram_bot_token configured")
    bot = TelegramClient(settings.telegram_bot_token)
    try:
        await bot.set_webhook(
            body.url,
            secret_token=settings.telegram_webhook_secret,
            drop_pending_updates=body.drop_pending,
        )
    except TelegramError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"ok": True, "url": body.url}


@router.post("/telegram/clear-webhook")
async def clear_webhook(settings: Settings = Depends(get_settings)):
    """Remove the webhook registration from Telegram."""
    if not settings.telegram_bot_token:
        raise HTTPException(400, "no telegram_bot_token configured")
    bot = TelegramClient(settings.telegram_bot_token)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except TelegramError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"ok": True}


@router.get("/telegram/info")
async def telegram_info(settings: Settings = Depends(get_settings)):
    """Return current webhook info and bot configuration."""
    if not settings.telegram_bot_token:
        raise HTTPException(400, "no telegram_bot_token configured")
    bot = TelegramClient(settings.telegram_bot_token)
    info = await bot.get_webhook_info()
    return {
        "bot_mode": settings.telegram_bot_mode,
        "webhook_info": info,
        "allowed_chats": list(allowed_chats(settings)),
    }
