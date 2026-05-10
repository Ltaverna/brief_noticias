import logging
from dataclasses import dataclass

import httpx
import trafilatura

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200


@dataclass(frozen=True)
class ExtractedContent:
    content: str | None
    has_full_text: bool


async def extract_content(
    client: httpx.AsyncClient, url: str, *, timeout: float = 15.0
) -> ExtractedContent:
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TransportError) as exc:
        logger.warning("extract_content fetch failed for %s: %s", url, exc)
        return ExtractedContent(content=None, has_full_text=False)

    extracted = trafilatura.extract(
        response.text, include_comments=False, include_tables=False, no_fallback=False
    )
    if extracted is None or len(extracted) < MIN_CONTENT_LENGTH:
        return ExtractedContent(content=extracted, has_full_text=False)
    return ExtractedContent(content=extracted, has_full_text=True)
