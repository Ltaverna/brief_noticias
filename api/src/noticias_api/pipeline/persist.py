import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article
from noticias_api.pipeline.fetch import FetchedItem

logger = logging.getLogger(__name__)


async def persist_items(
    session: AsyncSession, source_id: int, items: list[FetchedItem]
) -> int:
    if not items:
        return 0
    rows = [
        {
            "source_id": source_id,
            "external_id": item.external_id,
            "url": item.url,
            "title": item.title,
            "summary": item.summary,
            "published_at": item.published_at,
        }
        for item in items
    ]
    stmt = (
        insert(Article)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
        .returning(Article.id)
    )
    result = await session.execute(stmt)
    inserted_ids = result.scalars().all()
    await session.commit()
    return len(inserted_ids)
