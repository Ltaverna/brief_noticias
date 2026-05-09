import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article, Source
from noticias_api.pipeline.embed import embed_texts

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
) -> list[RetrievedChunk]:
    [vec] = await embed_texts(client, [query], model=embedding_model)
    rows = await session.execute(
        select(Article, Source)
        .join(Source, Source.id == Article.source_id)
        .where(Article.embedding.is_not(None))
        .order_by(Article.embedding.cosine_distance(vec))
        .limit(top_k)
    )
    out: list[RetrievedChunk] = []
    for article, source in rows.all():
        body = article.content or article.summary or ""
        text = f"{article.title}\n{body[:SNIPPET_CHARS]}"
        snippet = body[:240].strip().replace("\n", " ") if body else article.title
        out.append(
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
    return out
