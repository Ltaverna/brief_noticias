from datetime import datetime

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Source
from noticias_api.pipeline.fetch import FetchedItem
from noticias_api.pipeline.persist import persist_items


@pytest.mark.asyncio
async def test_persist_inserts_new_articles(db_session):
    src = Source(slug="test", name="Test", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    items = [
        FetchedItem(
            external_id="a1", url="https://x/a1", title="t1", summary="s1",
            published_at=datetime(2026, 5, 6, 14, 0),
        ),
        FetchedItem(
            external_id="a2", url="https://x/a2", title="t2", summary=None,
            published_at=None,
        ),
    ]
    inserted = await persist_items(db_session, src.id, items)
    assert inserted == 2

    rows = (await db_session.scalars(select(Article))).all()
    assert {r.external_id for r in rows} == {"a1", "a2"}


@pytest.mark.asyncio
async def test_persist_skips_duplicates(db_session):
    src = Source(slug="test", name="Test", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    items = [FetchedItem(external_id="a1", url="u", title="t", summary=None, published_at=None)]
    first = await persist_items(db_session, src.id, items)
    second = await persist_items(db_session, src.id, items)
    assert first == 1
    assert second == 0

    rows = (await db_session.scalars(select(Article))).all()
    assert len(rows) == 1
