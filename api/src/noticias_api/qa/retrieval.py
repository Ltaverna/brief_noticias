import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article, Source
from noticias_api.pipeline.embed import embed_texts
from noticias_api.qa.rerank import rerank_with_cohere

logger = logging.getLogger(__name__)

DEFAULT_TOP_K: Final = 20
SNIPPET_CHARS: Final = 1500


@dataclass(frozen=True)
class RetrievedChunk:
    article_id: int
    cluster_id: int | None
    source_slug: str
    source_name: str
    title: str
    url: str
    published_at: datetime | None
    text: str  # title + body excerpt for the LLM
    snippet: str  # shorter excerpt for the citation card


async def retrieve_chunks(
    session: AsyncSession,
    client: AsyncOpenAI,
    *,
    query: str,
    embedding_model: str,
    top_k: int = DEFAULT_TOP_K,
    hypothetical: str | None = None,
    settings=None,
) -> list[RetrievedChunk]:
    """Retrieve top_k chunks for the query.

    If `hypothetical` is provided it is embedded instead of the raw query (HyDE).

    If `settings.enable_reranking` and `settings.cohere_api_key` are truthy,
    kNN fetches `settings.rerank_initial_k` candidates first, then Cohere
    reranks to `top_k`. When reranking is unavailable or fails, the raw kNN
    order is used and results are sliced to `top_k`.
    """
    # Decide whether to rerank
    use_rerank = bool(
        settings
        and getattr(settings, "enable_reranking", False)
        and getattr(settings, "cohere_api_key", None)
    )
    initial_k = top_k
    if use_rerank:
        initial_k = max(initial_k, getattr(settings, "rerank_initial_k", 50))

    embed_text = hypothetical or query
    [vec] = await embed_texts(client, [embed_text], model=embedding_model)

    rows = await session.execute(
        select(Article, Source)
        .join(Source, Source.id == Article.source_id)
        .where(Article.embedding.is_not(None))
        .order_by(Article.embedding.cosine_distance(vec))
        .limit(initial_k)
    )
    chunks: list[RetrievedChunk] = []
    for article, source in rows.all():
        body = article.content or article.summary or ""
        text = f"{article.title}\n{body[:SNIPPET_CHARS]}"
        snippet = body[:240].strip().replace("\n", " ") if body else article.title
        chunks.append(
            RetrievedChunk(
                article_id=article.id,
                cluster_id=article.cluster_id,
                source_slug=source.slug,
                source_name=source.name,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                text=text,
                snippet=snippet,
            )
        )

    if use_rerank and chunks:
        try:
            results = await rerank_with_cohere(
                api_key=settings.cohere_api_key,
                query=query,
                documents=[c.text[:2000] for c in chunks],
                model=getattr(settings, "rerank_model", "rerank-multilingual-v3.0"),
                top_n=top_k,
            )
            chunks = [chunks[r.index] for r in results]
            logger.debug("cohere rerank selected %d chunks from %d candidates", len(chunks), initial_k)
        except Exception:
            logger.exception("rerank failed; falling back to raw kNN order")
            chunks = chunks[:top_k]
    else:
        chunks = chunks[:top_k]

    return chunks
