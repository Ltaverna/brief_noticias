from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from noticias_api.pipeline.extract import extract_content


@pytest.mark.asyncio
async def test_extract_returns_authors_from_html():
    fake_html = "<html><body>...</body></html>"
    http = MagicMock()
    response = MagicMock()
    response.text = fake_html
    response.raise_for_status = MagicMock()
    http.get = AsyncMock(return_value=response)

    fake_metadata = MagicMock()
    fake_metadata.text = "x" * 500
    fake_metadata.author = "Juan Pérez; María López"

    with patch("noticias_api.pipeline.extract.trafilatura.bare_extraction",
               return_value=fake_metadata):
        result = await extract_content(http, "http://x")

    assert result.has_full_text is True
    assert result.authors == ["Juan Pérez", "María López"]


@pytest.mark.asyncio
async def test_extract_no_authors_when_metadata_empty():
    http = MagicMock()
    response = MagicMock()
    response.text = "<html></html>"
    response.raise_for_status = MagicMock()
    http.get = AsyncMock(return_value=response)

    fake_metadata = MagicMock()
    fake_metadata.text = "x" * 500
    fake_metadata.author = None

    with patch("noticias_api.pipeline.extract.trafilatura.bare_extraction",
               return_value=fake_metadata):
        result = await extract_content(http, "http://x")

    assert result.authors == []


@pytest.mark.asyncio
async def test_extract_short_text_still_returns_authors():
    http = MagicMock()
    response = MagicMock()
    response.text = "<html></html>"
    response.raise_for_status = MagicMock()
    http.get = AsyncMock(return_value=response)

    fake_metadata = MagicMock()
    fake_metadata.text = "x" * 50  # below MIN_CONTENT_LENGTH
    fake_metadata.author = "Juan Pérez"

    with patch("noticias_api.pipeline.extract.trafilatura.bare_extraction",
               return_value=fake_metadata):
        result = await extract_content(http, "http://x")

    assert result.has_full_text is False
    assert result.authors == ["Juan Pérez"]
