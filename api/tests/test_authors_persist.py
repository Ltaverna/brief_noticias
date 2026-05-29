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
    a1 = await resolve_author(db_session, name="J. Pérez", source_id=source.id)
    a2 = await resolve_author(db_session, name="J Pérez", source_id=source.id)
    assert a1.id == a2.id
    await db_session.refresh(a1)
    assert "J" in a1.name


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
