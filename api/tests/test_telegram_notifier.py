import httpx
import pytest

from noticias_api.notifiers.telegram import (
    TelegramClient,
    TelegramError,
    escape_markdown_v2,
)


def test_escape_markdown_v2_passes_through_safe_chars():
    assert escape_markdown_v2("hola mundo") == "hola mundo"


def test_escape_markdown_v2_escapes_reserved():
    assert escape_markdown_v2("a.b!") == "a\\.b\\!"
    assert escape_markdown_v2("(hola)") == "\\(hola\\)"
    assert escape_markdown_v2("hash#tag") == "hash\\#tag"


def test_escape_markdown_v2_escapes_backslash():
    assert escape_markdown_v2("a\\b") == "a\\\\b"


@pytest.mark.asyncio
async def test_send_message_success(respx_mock):
    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(
            200, json={"ok": True, "result": {"message_id": 42}}
        )
    )
    client = TelegramClient(":ABC")
    msg_id = await client.send_message("123", "hola")
    assert msg_id == 42


@pytest.mark.asyncio
async def test_send_message_raises_on_http_error(respx_mock):
    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(500, text="server error")
    )
    client = TelegramClient(":ABC")
    with pytest.raises(TelegramError):
        await client.send_message("123", "hola")


@pytest.mark.asyncio
async def test_send_message_raises_on_api_not_ok(respx_mock):
    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(
            200, json={"ok": False, "description": "chat not found"}
        )
    )
    client = TelegramClient(":ABC")
    with pytest.raises(TelegramError, match="chat not found"):
        await client.send_message("123", "hola")
