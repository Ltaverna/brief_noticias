from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from noticias_api.pipeline.fetch import FetchedItem, fetch_feed, parse_feed

FIXTURE = Path(__file__).parent / "fixtures" / "feeds" / "sample_pagina12.xml"


def test_parse_feed_extracts_items():
    xml = FIXTURE.read_text()
    items = parse_feed(xml)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Inflación de abril fue del 4,2%"
    assert first.url == "https://www.pagina12.com.ar/123/inflacion-abril"
    assert first.external_id == "https://www.pagina12.com.ar/123/inflacion-abril"
    assert first.summary == "El INDEC informó hoy el dato de inflación del mes."
    assert first.published_at is not None


def test_parse_feed_skips_items_without_link_or_title():
    xml = """<?xml version="1.0"?><rss><channel>
      <item><title>solo titulo</title></item>
      <item><link>https://x/a</link></item>
      <item><title>ok</title><link>https://x/b</link><guid>https://x/b</guid></item>
    </channel></rss>"""
    items = parse_feed(xml)
    assert len(items) == 1
    assert items[0].title == "ok"


def test_parse_feed_filters_old_items():
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    xml = FIXTURE.read_text()
    items = parse_feed(xml, since=cutoff)
    # both items in fixture are older than 48h from now, so result is empty
    assert items == []


@pytest.mark.asyncio
async def test_fetch_feed_returns_xml_string(respx_mock):
    respx_mock.get("https://www.pagina12.com.ar/rss/portada").mock(
        return_value=httpx.Response(200, text=FIXTURE.read_text())
    )
    async with httpx.AsyncClient() as client:
        xml = await fetch_feed(client, "https://www.pagina12.com.ar/rss/portada")
    assert "Inflación" in xml


@pytest.mark.asyncio
async def test_fetch_feed_retries_once_on_5xx(respx_mock):
    route = respx_mock.get("https://example.com/rss").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, text="<rss><channel></channel></rss>"),
        ]
    )
    async with httpx.AsyncClient() as client:
        xml = await fetch_feed(client, "https://example.com/rss")
    assert route.call_count == 2
    assert "rss" in xml


@pytest.mark.asyncio
async def test_fetch_feed_raises_after_retries(respx_mock):
    respx_mock.get("https://example.com/rss").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_feed(client, "https://example.com/rss")
