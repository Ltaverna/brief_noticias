from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import respx as _respx
from fastapi.testclient import TestClient
from pytest_postgresql import factories
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from noticias_api.db.base import Base
from noticias_api.db.models import *  # noqa: F401, F403
from noticias_api.main import app
from noticias_api.db import session as session_module

postgresql_proc = factories.postgresql_noproc(
    host="localhost",
    port=5432,
    user="noticias",
    password="noticias",
)
postgresql = factories.postgresql("postgresql_proc", dbname="test_noticias")


@pytest_asyncio.fixture
async def db_engine(postgresql):
    # postgresql is a psycopg.Connection; info holds connection parameters
    info = postgresql.info
    url = (
        f"postgresql+psycopg://{info.user}:{info.password}@{info.host}:{info.port}/{info.dbname}"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest.fixture
def client(db_engine, monkeypatch) -> Iterator[TestClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(session_module, "async_session_factory", factory)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def respx_mock():
    with _respx.mock(assert_all_called=False) as mock:
        yield mock
