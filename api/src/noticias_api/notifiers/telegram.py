import logging
from typing import Final

import httpx

logger = logging.getLogger(__name__)

# Telegram MarkdownV2 reserved chars per official docs:
# https://core.telegram.org/bots/api#markdownv2-style
MD2_RESERVED: Final = r"_*[]()~`>#+-=|{}.!\\"


class TelegramError(Exception):
    """Raised when Telegram API returns a non-OK response."""


class TelegramClient:
    def __init__(self, bot_token: str, *, timeout: float = 15.0):
        self._url = f"https://api.telegram.org/bot{bot_token}"
        self._timeout = timeout

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str = "MarkdownV2",
        disable_web_page_preview: bool = True,
    ) -> int:
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            response = await http.post(
                f"{self._url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                },
            )
        if response.status_code != 200:
            raise TelegramError(
                f"telegram api {response.status_code}: {response.text[:200]}"
            )
        body = response.json()
        if not body.get("ok"):
            raise TelegramError(f"telegram error: {body.get('description')}")
        return body["result"]["message_id"]


    async def set_webhook(
        self,
        url: str,
        *,
        secret_token: str | None = None,
        drop_pending_updates: bool = False,
    ) -> bool:
        payload: dict = {"url": url, "drop_pending_updates": drop_pending_updates}
        if secret_token:
            payload["secret_token"] = secret_token
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(f"{self._url}/setWebhook", json=payload)
        body = r.json()
        if r.status_code != 200 or not body.get("ok"):
            raise TelegramError(f"setWebhook failed: {body.get('description')}")
        return True

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> bool:
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(
                f"{self._url}/deleteWebhook",
                json={"drop_pending_updates": drop_pending_updates},
            )
        body = r.json()
        if r.status_code != 200 or not body.get("ok"):
            raise TelegramError(f"deleteWebhook failed: {body.get('description')}")
        return True

    async def get_webhook_info(self) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.get(f"{self._url}/getWebhookInfo")
        return r.json().get("result", {})

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 25,
        limit: int = 50,
    ) -> list[dict]:
        payload: dict = {"timeout": timeout, "limit": limit}
        if offset is not None:
            payload["offset"] = offset
        async with httpx.AsyncClient(timeout=timeout + 10) as http:
            r = await http.post(f"{self._url}/getUpdates", json=payload)
        body = r.json()
        if not body.get("ok"):
            raise TelegramError(f"getUpdates failed: {body.get('description')}")
        return body.get("result", [])

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        *,
        parse_mode: str = "MarkdownV2",
        disable_web_page_preview: bool = True,
    ) -> None:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(f"{self._url}/editMessageText", json=payload)
        body = r.json()
        if r.status_code != 200 or not body.get("ok"):
            raise TelegramError(f"editMessageText failed: {body.get('description')}")


def escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 reserved characters with a backslash."""
    return "".join(f"\\{ch}" if ch in MD2_RESERVED else ch for ch in text)
