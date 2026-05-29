import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article, ArticleAuthor, Source
from noticias_api.pipeline.authors import ensure_synthetic, resolve_author
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
        .returning(Article.id, Article.external_id)
    )
    result = await session.execute(stmt)
    inserted = {ext_id: aid for aid, ext_id in result.all()}

    source = await session.get(Source, source_id)
    for item in items:
        article_id = inserted.get(item.external_id)
        if article_id is None:
            continue
        await _persist_authors_for_article(
            session, article_id=article_id, source=source, raw_authors=item.authors
        )

    await session.commit()
    return len(inserted)


async def _persist_authors_for_article(
    session: AsyncSession,
    *,
    article_id: int,
    source: Source,
    raw_authors: list[str],
) -> None:
    existing = await session.scalar(
        select(ArticleAuthor).where(ArticleAuthor.article_id == article_id)
    )
    if existing is not None:
        return

    if not raw_authors:
        synth = await ensure_synthetic(session, source=source)
        session.add(ArticleAuthor(article_id=article_id, author_id=synth.id, position=0))
        return

    seen: set[int] = set()
    pos = 0
    for name in raw_authors:
        author = await resolve_author(session, name=name, source_id=source.id)
        if author.id in seen:
            continue
        seen.add(author.id)
        session.add(
            ArticleAuthor(article_id=article_id, author_id=author.id, position=pos)
        )
        pos += 1


async def persist_authors_from_html(
    session: AsyncSession,
    *,
    article: Article,
    authors_from_html: list[str],
) -> None:
    """Called from extractor when RSS didn't bring authors."""
    existing = await session.scalar(
        select(ArticleAuthor).where(
            ArticleAuthor.article_id == article.id,
            ArticleAuthor.position == 0,
        )
    )
    # Only replace if the only thing there is the synthetic
    if existing:
        from noticias_api.db.models import Author
        author = await session.get(Author, existing.author_id)
        if not author or not author.is_synthetic:
            return
        from sqlalchemy import delete
        await session.execute(
            delete(ArticleAuthor).where(ArticleAuthor.article_id == article.id)
        )

    if not authors_from_html:
        return

    source = await session.get(Source, article.source_id)
    pos = 0
    seen: set[int] = set()
    for name in authors_from_html:
        author = await resolve_author(session, name=name, source_id=source.id)
        if author.id in seen:
            continue
        seen.add(author.id)
        session.add(
            ArticleAuthor(article_id=article.id, author_id=author.id, position=pos)
        )
        pos += 1
