import logging
from dataclasses import dataclass, field

import httpx
import trafilatura

from noticias_api.pipeline.authors import parse_byline

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200


@dataclass(frozen=True)
class ExtractedContent:
    content: str | None
    has_full_text: bool
    authors: list[str] = field(default_factory=list)


async def extract_content(
    client: httpx.AsyncClient, url: str, *, timeout: float = 15.0
) -> ExtractedContent:
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TransportError) as exc:
        logger.warning("extract_content fetch failed for %s: %s", url, exc)
        return ExtractedContent(content=None, has_full_text=False)

    try:
        meta = trafilatura.bare_extraction(
            response.text,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            with_metadata=True,
        )
    except Exception as exc:
        logger.warning("trafilatura.bare_extraction failed for %s: %s", url, exc)
        return ExtractedContent(content=None, has_full_text=False)

    if meta is None:
        return ExtractedContent(content=None, has_full_text=False)

    text = getattr(meta, "text", None)
    raw_author = getattr(meta, "author", None) or ""
    authors = parse_byline(raw_author)

    if text is None or len(text) < MIN_CONTENT_LENGTH:
        return ExtractedContent(content=text, has_full_text=False, authors=authors)
    return ExtractedContent(content=text, has_full_text=True, authors=authors)
