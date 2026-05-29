import logging
from dataclasses import dataclass, field
from datetime import datetime
from time import mktime

import feedparser
import httpx

from noticias_api.pipeline.authors import parse_byline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchedItem:
    external_id: str
    url: str
    title: str
    summary: str | None
    published_at: datetime | None
    authors: list[str] = field(default_factory=list)


def parse_feed(xml: str, since: datetime | None = None) -> list[FetchedItem]:
    parsed = feedparser.parse(xml)
    items: list[FetchedItem] = []
    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue
        external_id = entry.get("id") or entry.get("guid") or url
        summary = entry.get("summary")
        published_at: datetime | None = None
        if entry.get("published_parsed"):
            published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
        if since and published_at and published_at < since.replace(tzinfo=None):
            continue
        raw_author = entry.get("author") or entry.get("dc_creator") or ""
        if not raw_author and entry.get("authors"):
            raw_author = ", ".join(
                a.get("name", "") for a in entry.authors if a.get("name")
            )
        authors = parse_byline(raw_author)
        items.append(
            FetchedItem(
                external_id=external_id,
                url=url,
                title=title.strip(),
                summary=summary.strip() if summary else None,
                published_at=published_at,
                authors=authors,
            )
        )
    return items


async def fetch_feed(client: httpx.AsyncClient, url: str, *, timeout: float = 10.0) -> str:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            logger.warning("fetch_feed attempt %s failed: %s", attempt + 1, exc)
    assert last_exc is not None
    raise last_exc
