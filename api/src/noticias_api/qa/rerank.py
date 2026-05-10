import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RerankResult:
    index: int
    relevance_score: float


async def rerank_with_cohere(
    *,
    api_key: str,
    query: str,
    documents: list[str],
    model: str = "rerank-multilingual-v3.0",
    top_n: int = 10,
    timeout: float = 15.0,
) -> list[RerankResult]:
    """Rerank documents using the Cohere v2 rerank API.

    Returns an empty list immediately if `documents` is empty (no HTTP call).
    Raises `httpx.HTTPStatusError` on non-200 responses.
    """
    if not documents:
        return []
    async with httpx.AsyncClient(timeout=timeout) as http:
        r = await http.post(
            "https://api.cohere.com/v2/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(documents)),
            },
        )
    if r.status_code != 200:
        raise httpx.HTTPStatusError(
            f"cohere rerank {r.status_code}: {r.text[:200]}",
            request=r.request,
            response=r,
        )
    body = r.json()
    return [
        RerankResult(index=item["index"], relevance_score=item["relevance_score"])
        for item in body.get("results", [])
    ]
