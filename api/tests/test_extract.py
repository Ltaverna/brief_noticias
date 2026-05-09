from pathlib import Path

import httpx
import pytest

from noticias_api.pipeline.extract import ExtractedContent, extract_content

FIXTURE = Path(__file__).parent / "fixtures" / "html" / "sample_article.html"


@pytest.mark.asyncio
async def test_extract_content_parses_article(respx_mock):
    respx_mock.get("https://example.com/article").mock(
        return_value=httpx.Response(200, text=FIXTURE.read_text())
    )
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://example.com/article")
    assert result.has_full_text is True
    assert result.content is not None
    assert "INDEC" in result.content
    assert "menu" not in result.content
    assert "copyright" not in result.content


@pytest.mark.asyncio
async def test_extract_content_returns_no_full_text_when_short(respx_mock):
    respx_mock.get("https://paywall.com/x").mock(
        return_value=httpx.Response(
            200, text="<html><body><p>Suscribite para leer</p></body></html>"
        )
    )
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://paywall.com/x")
    assert result.has_full_text is False
    assert result.content is None or len(result.content) < 200


@pytest.mark.asyncio
async def test_extract_content_handles_5xx(respx_mock):
    respx_mock.get("https://broken.com/x").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://broken.com/x")
    assert result.has_full_text is False
    assert result.content is None
