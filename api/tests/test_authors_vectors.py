import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, ArticleAuthor, Author, Source
from noticias_api.pipeline.author_vectors import update_author_vectors


@pytest.fixture
async def source(db_session):
    src = Source(slug="clarin", name="Clarín", editorial_group="mainstream",
                 rss_url="http://x", base_url="http://x")
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)
    return src


@pytest.mark.asyncio
async def test_update_vectors_sets_centroid(db_session, source):
    author = Author(name="X", canonical="x", source_id=source.id, article_count=2)
    db_session.add(author)
    await db_session.flush()

    art1 = Article(source_id=source.id, external_id="e1", url="u1", title="t1",
                   embedding=[1.0] * 1536)
    art2 = Article(source_id=source.id, external_id="e2", url="u2", title="t2",
                   embedding=[3.0] * 1536)
    db_session.add_all([art1, art2])
    await db_session.flush()
    db_session.add_all([
        ArticleAuthor(article_id=art1.id, author_id=author.id, position=0),
        ArticleAuthor(article_id=art2.id, author_id=author.id, position=0),
    ])
    await db_session.commit()

    stats = await update_author_vectors(db_session)
    assert stats["updated"] == 1

    refreshed = await db_session.get(Author, author.id)
    assert refreshed.centroid is not None
    assert abs(refreshed.centroid[0] - 2.0) < 0.001
    assert refreshed.centroid_updated_at is not None


@pytest.mark.asyncio
async def test_update_vectors_skips_unchanged(db_session, source):
    # When article_count is 0, nothing to vectorize → skip
    author = Author(name="X", canonical="x", source_id=source.id,
                    article_count=0, centroid=[0.0] * 1536)
    db_session.add(author)
    await db_session.commit()
    stats = await update_author_vectors(db_session)
    assert stats["updated"] == 0
