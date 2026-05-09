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


def escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 reserved characters with a backslash."""
    return "".join(f"\\{ch}" if ch in MD2_RESERVED else ch for ch in text)
