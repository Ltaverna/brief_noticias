import pytest
from sqlalchemy import select

from noticias_api.db.models import Author, AuthorAlias, Source
from noticias_api.pipeline.authors import ensure_synthetic, resolve_author


@pytest.fixture
async def source(db_session):
    src = Source(slug="clarin", name="Clarín", editorial_group="mainstream",
                 rss_url="http://x", base_url="http://x")
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)
    return src


@pytest.mark.asyncio
async def test_resolve_author_creates_new(db_session, source):
    author = await resolve_author(db_session, name="Juan Pérez", source_id=source.id)
    assert author.id is not None
    assert author.canonical == "juan perez"
    assert author.source_id == source.id
    assert author.is_synthetic is False


@pytest.mark.asyncio
async def test_resolve_author_idempotent(db_session, source):
    a1 = await resolve_author(db_session, name="Juan Pérez", source_id=source.id)
    a2 = await resolve_author(db_session, name="Juan Pérez", source_id=source.id)
    assert a1.id == a2.id


@pytest.mark.asyncio
async def test_resolve_author_prefers_longer_display_name(db_session, source):
    # "J Pérez" and "J. Pérez" both canonicalize to "j perez"; the longer wins.
    a1 = await resolve_author(db_session, name="J Pérez", source_id=source.id)
    a2 = await resolve_author(db_session, name="J. Pérez", source_id=source.id)
    assert a1.id == a2.id
    await db_session.refresh(a1)
    assert a1.name == "J. Pérez"


@pytest.mark.asyncio
async def test_resolve_author_via_alias(db_session, source):
    real = await resolve_author(db_session, name="Juan Antonio Pérez", source_id=source.id)
    db_session.add(AuthorAlias(alias_canonical="j perez", author_id=real.id))
    await db_session.commit()
    resolved = await resolve_author(db_session, name="J. Pérez", source_id=source.id)
    assert resolved.id == real.id


@pytest.mark.asyncio
async def test_ensure_synthetic_creates_one_per_source(db_session, source):
    s1 = await ensure_synthetic(db_session, source=source)
    s2 = await ensure_synthetic(db_session, source=source)
    assert s1.id == s2.id
    assert s1.is_synthetic is True
    assert s1.source_id == source.id
    assert "Redacción" in s1.name


from noticias_api.db.models import Article, ArticleAuthor
from noticias_api.pipeline.fetch import FetchedItem
from noticias_api.pipeline.persist import persist_items


@pytest.mark.asyncio
async def test_persist_items_creates_author_links(db_session, source):
    items = [
        FetchedItem(
            external_id="x1", url="http://x/1", title="t1",
            summary=None, published_at=None,
            authors=["Juan Pérez"],
        )
    ]
    await persist_items(db_session, source.id, items)
    art = await db_session.scalar(select(Article).where(Article.external_id == "x1"))
    links = (await db_session.scalars(
        select(ArticleAuthor).where(ArticleAuthor.article_id == art.id)
    )).all()
    assert len(links) == 1


@pytest.mark.asyncio
async def test_persist_items_uses_synthetic_when_no_authors(db_session, source):
    items = [
        FetchedItem(external_id="x2", url="http://x/2", title="t2",
                    summary=None, published_at=None, authors=[])
    ]
    await persist_items(db_session, source.id, items)
    art = await db_session.scalar(select(Article).where(Article.external_id == "x2"))
    links = (await db_session.scalars(
        select(ArticleAuthor).where(ArticleAuthor.article_id == art.id)
    )).all()
    assert len(links) == 1
    author = await db_session.get(Author, links[0].author_id)
    assert author.is_synthetic is True


@pytest.mark.asyncio
async def test_persist_items_coauthorship_positions(db_session, source):
    items = [
        FetchedItem(external_id="x3", url="http://x/3", title="t3",
                    summary=None, published_at=None,
                    authors=["Juan Pérez", "María López"])
    ]
    await persist_items(db_session, source.id, items)
    art = await db_session.scalar(select(Article).where(Article.external_id == "x3"))
    links = (await db_session.scalars(
        select(ArticleAuthor)
        .where(ArticleAuthor.article_id == art.id)
        .order_by(ArticleAuthor.position)
    )).all()
    assert len(links) == 2
    assert links[0].position == 0
    assert links[1].position == 1


@pytest.mark.asyncio
async def test_persist_items_idempotent_authors(db_session, source):
    items = [
        FetchedItem(external_id="x4", url="http://x/4", title="t4",
                    summary=None, published_at=None,
                    authors=["Juan Pérez"])
    ]
    await persist_items(db_session, source.id, items)
    await persist_items(db_session, source.id, items)
    art = await db_session.scalar(select(Article).where(Article.external_id == "x4"))
    links = (await db_session.scalars(
        select(ArticleAuthor).where(ArticleAuthor.article_id == art.id)
    )).all()
    assert len(links) == 1
