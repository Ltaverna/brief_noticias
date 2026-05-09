import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 2000


def build_embedding_input(*, title: str, content: str | None, summary: str | None) -> str:
    body = (content or summary or "")[:MAX_CONTENT_CHARS]
    if body:
        return f"{title}\n\n{body}"
    return title


async def embed_texts(
    client: AsyncOpenAI, texts: list[str], *, model: str
) -> list[list[float]]:
    if not texts:
        return []
    # Pass dimensions=1536 so text-embedding-3-large fits our pgvector schema.
    # text-embedding-3-small ignores this param (its native size is 1536).
    response = await client.embeddings.create(
        model=model, input=texts, dimensions=1536
    )
    return [item.embedding for item in response.data]
