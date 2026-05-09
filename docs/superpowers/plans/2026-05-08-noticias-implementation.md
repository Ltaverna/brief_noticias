# Noticias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal web app that fetches news from 9 Argentine newspapers daily, clusters articles about the same event using embeddings, and produces structured editorial comparisons (common facts, per-source highlights, omissions, divergences) using GPT-4o.

**Architecture:** Python (FastAPI + APScheduler) backend with in-process pipeline + Next.js frontend. Postgres with pgvector for storage and embedding similarity search. OpenAI for embeddings and analysis. Single docker-compose for all three services.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2, httpx, feedparser, trafilatura, openai SDK, APScheduler, pytest. Next.js 15 (app router), React 19, Tailwind CSS 4, next-themes, pnpm. Postgres 16 with pgvector. Docker Compose.

**Spec:** `docs/superpowers/specs/2026-05-08-noticias-design.md`

---

## Phase 0: Project bootstrap

### Task 1: Repo structure and gitignore

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `.env.example`
- Create: `api/.gitkeep`
- Create: `web/.gitkeep`

- [ ] **Step 1: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Node
node_modules/
.next/
.pnpm-store/

# Env
.env
.env.local

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Project
backups/
*.dump
```

- [ ] **Step 2: Write `README.md` skeleton**

```markdown
# Noticias

Compara cómo distintos diarios argentinos cubren las mismas noticias.
Pipeline Python (FastAPI) + frontend Next.js + Postgres con pgvector.

## Quickstart

```bash
cp .env.example .env
# editar OPENAI_API_KEY en .env
docker compose up
```

API: http://localhost:8000 · Web: http://localhost:3000

## Estructura

- `api/` — backend Python, pipeline e API REST
- `web/` — frontend Next.js
- `docs/superpowers/` — specs y planes
```

- [ ] **Step 3: Write `.env.example`**

```
# OpenAI
OPENAI_API_KEY=sk-...

# Database
POSTGRES_USER=noticias
POSTGRES_PASSWORD=noticias
POSTGRES_DB=noticias
DATABASE_URL=postgresql+psycopg://noticias:noticias@postgres:5432/noticias

# API
API_PORT=8000
LOG_LEVEL=INFO

# Pipeline
CRON_HOUR=7
CRON_MINUTE=0
TOP_N_CLUSTERS=15
SIMILARITY_THRESHOLD=0.78

# Frontend
WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8000
INTERNAL_API_URL=http://api:8000
```

- [ ] **Step 4: Create empty placeholder files**

```bash
touch api/.gitkeep web/.gitkeep
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md .env.example api/.gitkeep web/.gitkeep
git commit -m "chore: repo skeleton, gitignore, env template"
```

---

### Task 2: docker-compose with Postgres + pgvector

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: ./api
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LOG_LEVEL: ${LOG_LEVEL}
      CRON_HOUR: ${CRON_HOUR}
      CRON_MINUTE: ${CRON_MINUTE}
      TOP_N_CLUSTERS: ${TOP_N_CLUSTERS}
      SIMILARITY_THRESHOLD: ${SIMILARITY_THRESHOLD}
    ports:
      - "${API_PORT}:8000"
    restart: unless-stopped

  web:
    build: ./web
    depends_on:
      - api
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
      INTERNAL_API_URL: ${INTERNAL_API_URL}
    ports:
      - "${WEB_PORT}:3000"
    restart: unless-stopped

volumes:
  postgres_data:
```

- [ ] **Step 2: Verify Postgres+pgvector starts**

```bash
docker compose up postgres -d
docker compose exec postgres psql -U noticias -d noticias -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Expected: a row with the pgvector version (e.g., `0.7.0` or similar).

- [ ] **Step 3: Stop the container**

```bash
docker compose down
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: docker-compose with postgres+pgvector, api, web services"
```

---

## Phase 1: API foundation

### Task 3: API project scaffolding

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/Dockerfile`
- Create: `api/.dockerignore`
- Create: `api/src/noticias_api/__init__.py`
- Create: `api/src/noticias_api/main.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/conftest.py`
- Create: `api/tests/test_healthz.py`

- [ ] **Step 1: Write `api/pyproject.toml`**

```toml
[project]
name = "noticias-api"
version = "0.1.0"
description = "Backend para comparador de noticias argentinas"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0",
    "psycopg[binary,pool]>=3.2",
    "alembic>=1.14",
    "pgvector>=0.3",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "httpx>=0.28",
    "feedparser>=6.0",
    "trafilatura>=2.0",
    "openai>=1.59",
    "apscheduler>=3.11",
    "orjson>=3.10",
    "python-dateutil>=2.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-postgresql>=6.1",
    "respx>=0.22",
    "ruff>=0.8",
    "mypy>=1.13",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/noticias_api"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]
```

- [ ] **Step 2: Write `api/Dockerfile`**

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY . .

EXPOSE 8000
CMD ["uvicorn", "noticias_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write `api/.dockerignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
tests/
```

- [ ] **Step 4: Write `api/src/noticias_api/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `api/src/noticias_api/main.py` (minimal)**

```python
from fastapi import FastAPI

app = FastAPI(title="Noticias API", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Write `api/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from noticias_api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 7: Write `api/tests/test_healthz.py`**

```python
def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 8: Install and run tests**

```bash
cd api && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_healthz.py -v
```

Expected: `test_healthz_returns_ok PASSED`

- [ ] **Step 9: Commit**

```bash
git add api/
git commit -m "feat(api): scaffold FastAPI app with healthz endpoint"
```

---

### Task 4: Configuration with Pydantic Settings

**Files:**
- Create: `api/src/noticias_api/config.py`
- Create: `api/tests/test_config.py`

- [ ] **Step 1: Write failing test `api/tests/test_config.py`**

```python
import os

import pytest

from noticias_api.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CRON_HOUR", "8")
    monkeypatch.setenv("TOP_N_CLUSTERS", "20")
    monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.80")

    s = Settings()

    assert s.database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert s.openai_api_key == "sk-test"
    assert s.cron_hour == 8
    assert s.top_n_clusters == 20
    assert s.similarity_threshold == 0.80


def test_settings_has_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    s = Settings()

    assert s.cron_hour == 7
    assert s.cron_minute == 0
    assert s.top_n_clusters == 15
    assert s.similarity_threshold == 0.78
    assert s.log_level == "INFO"
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: ImportError or `ModuleNotFoundError: noticias_api.config`.

- [ ] **Step 3: Write `api/src/noticias_api/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str
    openai_api_key: str

    log_level: str = "INFO"
    cron_hour: int = 7
    cron_minute: int = 0
    top_n_clusters: int = 15
    similarity_threshold: float = 0.78
    cluster_window_hours: int = 48
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chat_model_analysis: str = "gpt-4o"
    user_agent: str = "noticias-bot/0.1 (+https://github.com/personal/noticias)"
    max_concurrent_fetches: int = 8


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test, verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/config.py api/tests/test_config.py
git commit -m "feat(api): pydantic settings with env loading"
```

---

### Task 5: Database setup (SQLAlchemy + Alembic)

**Files:**
- Create: `api/src/noticias_api/db/__init__.py`
- Create: `api/src/noticias_api/db/session.py`
- Create: `api/src/noticias_api/db/base.py`
- Create: `api/alembic.ini`
- Create: `api/src/noticias_api/db/migrations/env.py`
- Create: `api/src/noticias_api/db/migrations/script.py.mako`
- Create: `api/src/noticias_api/db/migrations/versions/.gitkeep`

- [ ] **Step 1: Write `api/src/noticias_api/db/__init__.py`**

```python
from noticias_api.db.base import Base
from noticias_api.db.session import async_session_factory, get_session

__all__ = ["Base", "async_session_factory", "get_session"]
```

- [ ] **Step 2: Write `api/src/noticias_api/db/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 3: Write `api/src/noticias_api/db/session.py`**

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from noticias_api.config import get_settings

_engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

async_session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 4: Write `api/alembic.ini`**

```ini
[alembic]
script_location = src/noticias_api/db/migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@host/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5: Write `api/src/noticias_api/db/migrations/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from noticias_api.config import get_settings
from noticias_api.db.base import Base
from noticias_api.db import models  # noqa: F401  (registers models)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 6: Write `api/src/noticias_api/db/migrations/script.py.mako`**

```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7: Create empty models module placeholder**

```bash
mkdir -p api/src/noticias_api/db/migrations/versions
touch api/src/noticias_api/db/migrations/versions/.gitkeep
```

Create `api/src/noticias_api/db/models.py` with empty content (will be filled in next task):

```python
# Models will be added in Task 6
```

- [ ] **Step 8: Commit**

```bash
git add api/alembic.ini api/src/noticias_api/db/
git commit -m "feat(api): SQLAlchemy + Alembic plumbing"
```

---

### Task 6: Database models and initial migration

**Files:**
- Modify: `api/src/noticias_api/db/models.py`
- Create: `api/src/noticias_api/db/migrations/versions/0001_initial_schema.py`
- Create: `api/tests/test_models.py`

- [ ] **Step 1: Write `api/src/noticias_api/db/models.py` with all models**

```python
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from noticias_api.db.base import Base

EMBEDDING_DIM = 1536


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    editorial_group: Mapped[str] = mapped_column(String(32), nullable=False)
    rss_url: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    articles: Mapped[list["Article"]] = relationship(back_populates="source")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    centroid: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    article_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    display_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    articles: Mapped[list["Article"]] = relationship(back_populates="cluster")
    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="cluster", uselist=False, cascade="all, delete-orphan"
    )


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_articles_source_ext"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_full_text: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True
    )

    source: Mapped[Source] = relationship(back_populates="articles")
    cluster: Mapped[Cluster | None] = relationship(back_populates="articles")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_facts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    by_source: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    omissions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    divergences: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cluster: Mapped[Cluster] = relationship(back_populates="analysis")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: Write `api/tests/test_models.py`**

```python
from noticias_api.db.models import Analysis, Article, Cluster, Run, Source


def test_models_are_registered():
    assert Source.__tablename__ == "sources"
    assert Article.__tablename__ == "articles"
    assert Cluster.__tablename__ == "clusters"
    assert Analysis.__tablename__ == "analyses"
    assert Run.__tablename__ == "runs"


def test_articles_have_unique_source_external_id():
    constraints = [c.name for c in Article.__table_args__]
    assert "uq_articles_source_ext" in constraints
```

- [ ] **Step 3: Run model tests**

```bash
pytest tests/test_models.py -v
```

Expected: 2 PASSED.

- [ ] **Step 4: Generate the initial migration**

Start postgres:

```bash
docker compose up postgres -d
sleep 3
docker compose exec postgres psql -U noticias -d noticias -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

From `api/`:

```bash
DATABASE_URL=postgresql+psycopg://noticias:noticias@localhost:5432/noticias \
  alembic revision --autogenerate -m "initial schema"
```

This creates `api/src/noticias_api/db/migrations/versions/<hash>_initial_schema.py`.

- [ ] **Step 5: Edit the generated migration to add pgvector extension and HNSW indexes**

Open the generated file. At the very top of `upgrade()`, add:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

At the end of `upgrade()` (after `op.create_table` calls), add:

```python
op.execute(
    "CREATE INDEX ix_articles_embedding_hnsw ON articles "
    "USING hnsw (embedding vector_cosine_ops)"
)
op.execute(
    "CREATE INDEX ix_clusters_centroid_hnsw ON clusters "
    "USING hnsw (centroid vector_cosine_ops)"
)
op.execute("CREATE INDEX ix_articles_published_at ON articles (published_at DESC)")
op.execute("CREATE INDEX ix_articles_cluster_id ON articles (cluster_id)")
op.execute("CREATE INDEX ix_clusters_display_date ON clusters (display_date DESC) WHERE is_top")
```

In `downgrade()`, add at the top:

```python
op.execute("DROP INDEX IF EXISTS ix_clusters_display_date")
op.execute("DROP INDEX IF EXISTS ix_articles_cluster_id")
op.execute("DROP INDEX IF EXISTS ix_articles_published_at")
op.execute("DROP INDEX IF EXISTS ix_clusters_centroid_hnsw")
op.execute("DROP INDEX IF EXISTS ix_articles_embedding_hnsw")
```

- [ ] **Step 6: Apply the migration**

```bash
DATABASE_URL=postgresql+psycopg://noticias:noticias@localhost:5432/noticias \
  alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade -> <hash>, initial schema`

- [ ] **Step 7: Verify schema**

```bash
docker compose exec postgres psql -U noticias -d noticias -c "\dt"
```

Expected: 6 tables (5 model tables + `alembic_version`).

```bash
docker compose exec postgres psql -U noticias -d noticias -c "\di"
```

Expected: HNSW indexes on `articles.embedding` and `clusters.centroid`.

- [ ] **Step 8: Rename migration file to canonical name**

```bash
cd api/src/noticias_api/db/migrations/versions/
ls
# rename the generated file (e.g., abc123_initial_schema.py) to:
mv *_initial_schema.py 0001_initial_schema.py
```

Edit the file: change the line `revision: str = "<hash>"` to keep the hash but ensure the filename references it consistently.

- [ ] **Step 9: Commit**

```bash
git add api/src/noticias_api/db/models.py api/src/noticias_api/db/migrations/versions/0001_initial_schema.py api/tests/test_models.py
git commit -m "feat(api): initial schema with sources, articles, clusters, analyses, runs"
```

---

### Task 7: Sources seed and endpoints

**Files:**
- Create: `api/src/noticias_api/db/seed.py`
- Create: `api/src/noticias_api/api/__init__.py`
- Create: `api/src/noticias_api/api/sources.py`
- Modify: `api/src/noticias_api/main.py`
- Create: `api/tests/test_sources_api.py`
- Create: `api/tests/conftest_db.py`

- [ ] **Step 1: Write `api/src/noticias_api/db/seed.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Source

SEED_SOURCES: list[dict[str, str]] = [
    {
        "slug": "la-nacion",
        "name": "La Nación",
        "editorial_group": "mainstream",
        "rss_url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
        "base_url": "https://www.lanacion.com.ar",
    },
    {
        "slug": "clarin",
        "name": "Clarín",
        "editorial_group": "mainstream",
        "rss_url": "https://www.clarin.com/rss/lo-ultimo/",
        "base_url": "https://www.clarin.com",
    },
    {
        "slug": "infobae",
        "name": "Infobae",
        "editorial_group": "mainstream",
        "rss_url": "https://www.infobae.com/feeds/rss/",
        "base_url": "https://www.infobae.com",
    },
    {
        "slug": "pagina-12",
        "name": "Página 12",
        "editorial_group": "critico",
        "rss_url": "https://www.pagina12.com.ar/rss/portada",
        "base_url": "https://www.pagina12.com.ar",
    },
    {
        "slug": "tiempo-argentino",
        "name": "Tiempo Argentino",
        "editorial_group": "critico",
        "rss_url": "https://www.tiempoar.com.ar/feed/",
        "base_url": "https://www.tiempoar.com.ar",
    },
    {
        "slug": "el-destape",
        "name": "El Destape",
        "editorial_group": "critico",
        "rss_url": "https://www.eldestapeweb.com/rss/portada.xml",
        "base_url": "https://www.eldestapeweb.com",
    },
    {
        "slug": "ambito",
        "name": "Ámbito",
        "editorial_group": "economico",
        "rss_url": "https://www.ambito.com/rss/pages/home.xml",
        "base_url": "https://www.ambito.com",
    },
    {
        "slug": "el-cronista",
        "name": "El Cronista",
        "editorial_group": "economico",
        "rss_url": "https://www.cronista.com/feed/",
        "base_url": "https://www.cronista.com",
    },
    {
        "slug": "bae",
        "name": "BAE Negocios",
        "editorial_group": "economico",
        "rss_url": "https://www.baenegocios.com/rss/portada.xml",
        "base_url": "https://www.baenegocios.com",
    },
]


async def seed_sources(session: AsyncSession) -> int:
    inserted = 0
    for data in SEED_SOURCES:
        existing = await session.scalar(select(Source).where(Source.slug == data["slug"]))
        if existing:
            continue
        session.add(Source(**data))
        inserted += 1
    await session.commit()
    return inserted
```

- [ ] **Step 2: Write `api/tests/conftest_db.py` (DB fixture using pytest-postgresql)**

Replace `api/tests/conftest.py` with:

```python
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_postgresql import factories
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from noticias_api.db.base import Base
from noticias_api.db.models import *  # noqa: F401, F403
from noticias_api.main import app
from noticias_api.db import session as session_module

postgresql_proc = factories.postgresql_proc(load=["CREATE EXTENSION IF NOT EXISTS vector;"])
postgresql = factories.postgresql("postgresql_proc")


@pytest_asyncio.fixture
async def db_engine(postgresql):
    info = postgresql.info
    url = (
        f"postgresql+psycopg://{info.user}:@{info.host}:{info.port}/{info.dbname}"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
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
```

Delete the old `api/tests/conftest.py` if separate:

```bash
# (already replaced above; ensure only one conftest exists)
```

- [ ] **Step 3: Write failing test `api/tests/test_sources_api.py`**

```python
import pytest

from noticias_api.db.seed import seed_sources


@pytest.mark.asyncio
async def test_get_sources_returns_seeded_list(db_session, client):
    inserted = await seed_sources(db_session)
    assert inserted == 9

    response = client.get("/sources")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 9
    slugs = {s["slug"] for s in body}
    assert slugs == {
        "la-nacion", "clarin", "infobae",
        "pagina-12", "tiempo-argentino", "el-destape",
        "ambito", "el-cronista", "bae",
    }


@pytest.mark.asyncio
async def test_patch_source_toggles_enabled(db_session, client):
    await seed_sources(db_session)

    response = client.patch("/sources/la-nacion", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.get("/sources")
    la_nacion = next(s for s in response.json() if s["slug"] == "la-nacion")
    assert la_nacion["enabled"] is False
```

- [ ] **Step 4: Run test, verify it fails**

```bash
pytest tests/test_sources_api.py -v
```

Expected: 404 (endpoints don't exist yet).

- [ ] **Step 5: Write `api/src/noticias_api/api/__init__.py`**

```python
```

- [ ] **Step 6: Write `api/src/noticias_api/api/sources.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["sources"])


class SourceOut(BaseModel):
    slug: str
    name: str
    editorial_group: str
    rss_url: str
    base_url: str
    enabled: bool


class SourcePatch(BaseModel):
    enabled: bool


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[Source]:
    result = await session.scalars(select(Source).order_by(Source.editorial_group, Source.name))
    return list(result.all())


@router.patch("/sources/{slug}", response_model=SourceOut)
async def update_source(
    slug: str, patch: SourcePatch, session: AsyncSession = Depends(get_session)
) -> Source:
    source = await session.scalar(select(Source).where(Source.slug == slug))
    if not source:
        raise HTTPException(status_code=404, detail=f"source '{slug}' not found")
    source.enabled = patch.enabled
    await session.commit()
    await session.refresh(source)
    return source
```

- [ ] **Step 7: Wire router into `api/src/noticias_api/main.py`**

Replace existing content with:

```python
from fastapi import FastAPI

from noticias_api.api import sources

app = FastAPI(title="Noticias API", version="0.1.0")
app.include_router(sources.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 8: Run tests, verify pass**

```bash
pytest tests/test_sources_api.py -v
```

Expected: 2 PASSED.

- [ ] **Step 9: Commit**

```bash
git add api/src/noticias_api/db/seed.py api/src/noticias_api/api/ api/src/noticias_api/main.py api/tests/conftest.py api/tests/test_sources_api.py
git commit -m "feat(api): seed 9 sources, GET /sources, PATCH /sources/:slug"
```

---

## Phase 2: Pipeline steps (TDD per step)

Each pipeline step lives in `api/src/noticias_api/pipeline/`. Steps are pure functions that take inputs (often a DB session and config) and return data the orchestrator persists. This makes each step independently testable.

### Task 8: Pipeline step — fetch RSS

**Files:**
- Create: `api/src/noticias_api/pipeline/__init__.py`
- Create: `api/src/noticias_api/pipeline/fetch.py`
- Create: `api/tests/fixtures/feeds/sample_pagina12.xml`
- Create: `api/tests/test_fetch.py`

- [ ] **Step 1: Save a sample RSS fixture**

Create `api/tests/fixtures/feeds/sample_pagina12.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Página 12</title>
    <link>https://www.pagina12.com.ar</link>
    <description>Noticias</description>
    <item>
      <title>Inflación de abril fue del 4,2%</title>
      <link>https://www.pagina12.com.ar/123/inflacion-abril</link>
      <guid>https://www.pagina12.com.ar/123/inflacion-abril</guid>
      <description>El INDEC informó hoy el dato de inflación del mes.</description>
      <pubDate>Mon, 06 May 2026 14:00:00 -0300</pubDate>
    </item>
    <item>
      <title>Boca venció a River por 2-1</title>
      <link>https://www.pagina12.com.ar/124/superclasico</link>
      <guid>https://www.pagina12.com.ar/124/superclasico</guid>
      <description>El partido se jugó en La Bombonera.</description>
      <pubDate>Sun, 05 May 2026 22:30:00 -0300</pubDate>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write failing test `api/tests/test_fetch.py`**

```python
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from noticias_api.pipeline.fetch import FetchedItem, fetch_feed, parse_feed

FIXTURE = Path(__file__).parent / "fixtures" / "feeds" / "sample_pagina12.xml"


def test_parse_feed_extracts_items():
    xml = FIXTURE.read_text()
    items = parse_feed(xml)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Inflación de abril fue del 4,2%"
    assert first.url == "https://www.pagina12.com.ar/123/inflacion-abril"
    assert first.external_id == "https://www.pagina12.com.ar/123/inflacion-abril"
    assert first.summary == "El INDEC informó hoy el dato de inflación del mes."
    assert first.published_at is not None


def test_parse_feed_skips_items_without_link_or_title():
    xml = """<?xml version="1.0"?><rss><channel>
      <item><title>solo titulo</title></item>
      <item><link>https://x/a</link></item>
      <item><title>ok</title><link>https://x/b</link><guid>https://x/b</guid></item>
    </channel></rss>"""
    items = parse_feed(xml)
    assert len(items) == 1
    assert items[0].title == "ok"


def test_parse_feed_filters_old_items():
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    xml = FIXTURE.read_text()
    items = parse_feed(xml, since=cutoff)
    # both items in fixture are older than 48h from now, so result is empty
    assert items == []


@pytest.mark.asyncio
async def test_fetch_feed_returns_xml_string(respx_mock):
    respx_mock.get("https://www.pagina12.com.ar/rss/portada").mock(
        return_value=httpx.Response(200, text=FIXTURE.read_text())
    )
    async with httpx.AsyncClient() as client:
        xml = await fetch_feed(client, "https://www.pagina12.com.ar/rss/portada")
    assert "Inflación" in xml


@pytest.mark.asyncio
async def test_fetch_feed_retries_once_on_5xx(respx_mock):
    route = respx_mock.get("https://example.com/rss").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, text="<rss><channel></channel></rss>"),
        ]
    )
    async with httpx.AsyncClient() as client:
        xml = await fetch_feed(client, "https://example.com/rss")
    assert route.call_count == 2
    assert "rss" in xml


@pytest.mark.asyncio
async def test_fetch_feed_raises_after_retries(respx_mock):
    respx_mock.get("https://example.com/rss").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_feed(client, "https://example.com/rss")
```

Add `respx` fixture to `conftest.py` at the bottom:

```python
import respx as _respx


@pytest.fixture
def respx_mock():
    with _respx.mock(assert_all_called=False) as mock:
        yield mock
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
pytest tests/test_fetch.py -v
```

Expected: ImportError on `noticias_api.pipeline.fetch`.

- [ ] **Step 4: Write `api/src/noticias_api/pipeline/__init__.py`**

```python
```

- [ ] **Step 5: Write `api/src/noticias_api/pipeline/fetch.py`**

```python
import logging
from dataclasses import dataclass
from datetime import datetime
from time import mktime

import feedparser
import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchedItem:
    external_id: str
    url: str
    title: str
    summary: str | None
    published_at: datetime | None


def parse_feed(xml: str, since: datetime | None = None) -> list[FetchedItem]:
    parsed = feedparser.parse(xml)
    items: list[FetchedItem] = []
    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue
        external_id = entry.get("id") or entry.get("guid") or url
        summary = entry.get("summary")
        published_at: datetime | None = None
        if entry.get("published_parsed"):
            published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
        if since and published_at and published_at < since.replace(tzinfo=None):
            continue
        items.append(
            FetchedItem(
                external_id=external_id,
                url=url,
                title=title.strip(),
                summary=summary.strip() if summary else None,
                published_at=published_at,
            )
        )
    return items


async def fetch_feed(client: httpx.AsyncClient, url: str, *, timeout: float = 10.0) -> str:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            logger.warning("fetch_feed attempt %s failed: %s", attempt + 1, exc)
    assert last_exc is not None
    raise last_exc
```

- [ ] **Step 6: Run tests, verify they pass**

```bash
pytest tests/test_fetch.py -v
```

Expected: 5 PASSED.

- [ ] **Step 7: Commit**

```bash
git add api/src/noticias_api/pipeline/ api/tests/fixtures/feeds/ api/tests/test_fetch.py api/tests/conftest.py
git commit -m "feat(pipeline): RSS fetch with feedparser and retry"
```

---

### Task 9: Pipeline step — persist articles (dedupe)

**Files:**
- Create: `api/src/noticias_api/pipeline/persist.py`
- Create: `api/tests/test_persist.py`

- [ ] **Step 1: Write failing test `api/tests/test_persist.py`**

```python
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
```

- [ ] **Step 2: Run, verify fails**

```bash
pytest tests/test_persist.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write `api/src/noticias_api/pipeline/persist.py`**

```python
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
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_persist.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/pipeline/persist.py api/tests/test_persist.py
git commit -m "feat(pipeline): persist articles with on-conflict-do-nothing dedupe"
```

---

### Task 10: Pipeline step — extract full text

**Files:**
- Create: `api/src/noticias_api/pipeline/extract.py`
- Create: `api/tests/fixtures/html/sample_article.html`
- Create: `api/tests/test_extract.py`

- [ ] **Step 1: Save HTML fixture**

Create `api/tests/fixtures/html/sample_article.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head><title>Inflación de abril</title></head>
<body>
  <header>menu</header>
  <article>
    <h1>Inflación de abril fue del 4,2% según el INDEC</h1>
    <p>El Instituto Nacional de Estadística y Censos publicó hoy el dato.
    La acumulada de los últimos doce meses se ubicó en 142%.</p>
    <p>Los rubros que más subieron fueron alimentos y servicios públicos.
    El Gobierno destacó la desaceleración respecto del mes anterior.</p>
  </article>
  <footer>copyright</footer>
</body>
</html>
```

- [ ] **Step 2: Write failing test `api/tests/test_extract.py`**

```python
from pathlib import Path

import httpx
import pytest

from noticias_api.pipeline.extract import ExtractedContent, extract_content

FIXTURE = Path(__file__).parent / "fixtures" / "html" / "sample_article.html"


@pytest.mark.asyncio
async def test_extract_content_parses_article(respx_mock):
    respx_mock.get("https://example.com/article").mock(
        return_value=httpx.Response(200, text=FIXTURE.read_text())
    )
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://example.com/article")
    assert result.has_full_text is True
    assert result.content is not None
    assert "INDEC" in result.content
    assert "menu" not in result.content
    assert "copyright" not in result.content


@pytest.mark.asyncio
async def test_extract_content_returns_no_full_text_when_short(respx_mock):
    respx_mock.get("https://paywall.com/x").mock(
        return_value=httpx.Response(
            200, text="<html><body><p>Suscribite para leer</p></body></html>"
        )
    )
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://paywall.com/x")
    assert result.has_full_text is False
    assert result.content is None or len(result.content) < 200


@pytest.mark.asyncio
async def test_extract_content_handles_5xx(respx_mock):
    respx_mock.get("https://broken.com/x").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        result = await extract_content(client, "https://broken.com/x")
    assert result.has_full_text is False
    assert result.content is None
```

- [ ] **Step 3: Run, verify fails**

```bash
pytest tests/test_extract.py -v
```

Expected: ImportError.

- [ ] **Step 4: Write `api/src/noticias_api/pipeline/extract.py`**

```python
import logging
from dataclasses import dataclass

import httpx
import trafilatura

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200


@dataclass(frozen=True)
class ExtractedContent:
    content: str | None
    has_full_text: bool


async def extract_content(
    client: httpx.AsyncClient, url: str, *, timeout: float = 15.0
) -> ExtractedContent:
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TransportError) as exc:
        logger.warning("extract_content fetch failed for %s: %s", url, exc)
        return ExtractedContent(content=None, has_full_text=False)

    extracted = trafilatura.extract(
        response.text, include_comments=False, include_tables=False, no_fallback=False
    )
    if extracted is None or len(extracted) < MIN_CONTENT_LENGTH:
        return ExtractedContent(content=extracted, has_full_text=False)
    return ExtractedContent(content=extracted, has_full_text=True)
```

- [ ] **Step 5: Run, verify pass**

```bash
pytest tests/test_extract.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add api/src/noticias_api/pipeline/extract.py api/tests/fixtures/html/ api/tests/test_extract.py
git commit -m "feat(pipeline): extract article content with trafilatura"
```

---

### Task 11: Pipeline step — embeddings

**Files:**
- Create: `api/src/noticias_api/pipeline/embed.py`
- Create: `api/tests/test_embed.py`

- [ ] **Step 1: Write failing test `api/tests/test_embed.py`**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.pipeline.embed import build_embedding_input, embed_texts


def test_build_embedding_input_uses_content_when_available():
    text = build_embedding_input(
        title="Inflación abril",
        content="El INDEC informó " * 100,  # long
        summary="resumen",
    )
    assert text.startswith("Inflación abril\n\n")
    assert "INDEC" in text
    assert "resumen" not in text  # content takes priority


def test_build_embedding_input_falls_back_to_summary():
    text = build_embedding_input(
        title="Boca-River", content=None, summary="El partido fue 2-1."
    )
    assert "Boca-River" in text
    assert "2-1" in text


def test_build_embedding_input_truncates_content():
    long_content = "a" * 10000
    text = build_embedding_input(title="x", content=long_content, summary=None)
    assert len(text) < 2100  # title + sep + 2000 chars max


@pytest.mark.asyncio
async def test_embed_texts_batches_calls():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(3)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_response)

    embeddings = await embed_texts(fake_client, ["a", "b", "c"], model="text-embedding-3-small")

    assert len(embeddings) == 3
    assert all(len(e) == 1536 for e in embeddings)
    fake_client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-3-small", input=["a", "b", "c"]
    )


@pytest.mark.asyncio
async def test_embed_texts_returns_empty_for_empty_input():
    fake_client = MagicMock()
    embeddings = await embed_texts(fake_client, [], model="text-embedding-3-small")
    assert embeddings == []
```

- [ ] **Step 2: Run, verify fails**

```bash
pytest tests/test_embed.py -v
```

- [ ] **Step 3: Write `api/src/noticias_api/pipeline/embed.py`**

```python
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
    response = await client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_embed.py -v
```

Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/pipeline/embed.py api/tests/test_embed.py
git commit -m "feat(pipeline): OpenAI embeddings batching"
```

---

### Task 12: Pipeline step — clustering

**Files:**
- Create: `api/src/noticias_api/pipeline/cluster.py`
- Create: `api/tests/test_cluster.py`

- [ ] **Step 1: Write failing test `api/tests/test_cluster.py`**

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Cluster, Source
from noticias_api.pipeline.cluster import cluster_recent_articles


def _vec(value: float, dim: int = 1536) -> list[float]:
    """Create a unit-ish vector pointing in a 'direction'."""
    v = [value] + [0.001] * (dim - 1)
    return v


@pytest.mark.asyncio
async def test_similar_articles_share_cluster(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    a = Article(source_id=src.id, external_id="a", url="u1", title="Inflación",
                embedding=_vec(1.0), published_at=now)
    b = Article(source_id=src.id, external_id="b", url="u2", title="Inflacion",
                embedding=_vec(1.0), published_at=now)
    db_session.add_all([a, b])
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    rows = (await db_session.scalars(select(Article).order_by(Article.id))).all()
    assert rows[0].cluster_id is not None
    assert rows[0].cluster_id == rows[1].cluster_id


@pytest.mark.asyncio
async def test_dissimilar_articles_get_separate_clusters(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    inflation = [1.0] + [0.0] * 1535
    soccer = [0.0] * 1535 + [1.0]
    a = Article(source_id=src.id, external_id="a", url="u1", title="Inflación",
                embedding=inflation, published_at=now)
    b = Article(source_id=src.id, external_id="b", url="u2", title="Boca-River",
                embedding=soccer, published_at=now)
    db_session.add_all([a, b])
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    rows = (await db_session.scalars(select(Article).order_by(Article.id))).all()
    assert rows[0].cluster_id != rows[1].cluster_id


@pytest.mark.asyncio
async def test_articles_outside_window_are_not_clustered(db_session):
    src = Source(slug="s1", name="S1", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    old = datetime.now(UTC) - timedelta(hours=72)
    a = Article(source_id=src.id, external_id="a", url="u1", title="x",
                embedding=_vec(1.0), published_at=old)
    db_session.add(a)
    await db_session.commit()

    await cluster_recent_articles(db_session, threshold=0.78, window_hours=48)

    refreshed = await db_session.get(Article, a.id)
    assert refreshed.cluster_id is None
```

- [ ] **Step 2: Run, verify fails**

```bash
pytest tests/test_cluster.py -v
```

- [ ] **Step 3: Write `api/src/noticias_api/pipeline/cluster.py`**

```python
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Article, Cluster

logger = logging.getLogger(__name__)


async def cluster_recent_articles(
    session: AsyncSession, *, threshold: float, window_hours: int
) -> dict[str, int]:
    """Assign cluster_id to articles in the time window using kNN over embeddings.

    Algorithm: for each article without a cluster, find the most similar article
    in the window that already has a cluster. If similarity >= threshold, join
    that cluster. Otherwise, create a new cluster. Cosine similarity = 1 - cosine_distance.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    new_articles = (
        await session.scalars(
            select(Article)
            .where(Article.published_at >= cutoff)
            .where(Article.cluster_id.is_(None))
            .where(Article.embedding.is_not(None))
            .order_by(Article.published_at)
        )
    ).all()

    stats = {"clustered": 0, "new_clusters": 0}

    for article in new_articles:
        # find nearest neighbor with a cluster, within window
        nearest = await session.execute(
            select(
                Article.cluster_id,
                (1 - Article.embedding.cosine_distance(article.embedding)).label("sim"),
            )
            .where(Article.id != article.id)
            .where(Article.published_at >= cutoff)
            .where(Article.cluster_id.is_not(None))
            .where(Article.embedding.is_not(None))
            .order_by(Article.embedding.cosine_distance(article.embedding))
            .limit(1)
        )
        row = nearest.first()

        if row and row.sim >= threshold:
            article.cluster_id = row.cluster_id
        else:
            new_cluster = Cluster(centroid=article.embedding)
            session.add(new_cluster)
            await session.flush()
            article.cluster_id = new_cluster.id
            stats["new_clusters"] += 1
        stats["clustered"] += 1

    await session.commit()
    await _refresh_cluster_stats(session, cutoff)
    return stats


async def _refresh_cluster_stats(session: AsyncSession, cutoff: datetime) -> None:
    """Recompute article_count, source_count, last_seen_at for affected clusters."""
    cluster_ids = (
        await session.scalars(
            select(Article.cluster_id)
            .where(Article.cluster_id.is_not(None))
            .where(Article.published_at >= cutoff)
            .distinct()
        )
    ).all()

    for cid in cluster_ids:
        agg = (
            await session.execute(
                select(
                    func.count(Article.id).label("ac"),
                    func.count(func.distinct(Article.source_id)).label("sc"),
                    func.max(Article.published_at).label("last"),
                ).where(Article.cluster_id == cid)
            )
        ).one()
        await session.execute(
            update(Cluster)
            .where(Cluster.id == cid)
            .values(article_count=agg.ac, source_count=agg.sc, last_seen_at=agg.last)
        )
    await session.commit()
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_cluster.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/pipeline/cluster.py api/tests/test_cluster.py
git commit -m "feat(pipeline): kNN clustering with cosine similarity threshold"
```

---

### Task 13: Pipeline step — ranking

**Files:**
- Create: `api/src/noticias_api/pipeline/rank.py`
- Create: `api/tests/test_rank.py`

- [ ] **Step 1: Write failing test `api/tests/test_rank.py`**

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Cluster, Source
from noticias_api.pipeline.rank import rank_top_clusters


@pytest.mark.asyncio
async def test_rank_marks_top_n_with_highest_score(db_session):
    sources = [
        Source(slug=f"s{i}", name=f"S{i}", editorial_group="mainstream",
               rss_url="x", base_url="x")
        for i in range(5)
    ]
    db_session.add_all(sources)
    await db_session.commit()

    now = datetime.now(UTC)
    # cluster A: 4 sources, recent → high score
    cluster_a = Cluster(article_count=4, source_count=4, last_seen_at=now)
    # cluster B: 2 sources, recent → medium
    cluster_b = Cluster(article_count=2, source_count=2, last_seen_at=now)
    # cluster C: 1 source → filtered out (below source_count >= 2)
    cluster_c = Cluster(article_count=1, source_count=1, last_seen_at=now)
    db_session.add_all([cluster_a, cluster_b, cluster_c])
    await db_session.commit()

    await rank_top_clusters(db_session, top_n=10)

    rows = (await db_session.scalars(select(Cluster).where(Cluster.is_top))).all()
    top_ids = {r.id for r in rows}
    assert cluster_a.id in top_ids
    assert cluster_b.id in top_ids
    assert cluster_c.id not in top_ids  # filtered by min source_count


@pytest.mark.asyncio
async def test_rank_respects_top_n_cap(db_session):
    src = Source(slug="s", name="S", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    now = datetime.now(UTC)
    clusters = [
        Cluster(article_count=2, source_count=2, last_seen_at=now - timedelta(hours=i))
        for i in range(20)
    ]
    db_session.add_all(clusters)
    await db_session.commit()

    await rank_top_clusters(db_session, top_n=5)

    top_count = await db_session.scalar(
        select(__import__("sqlalchemy").func.count(Cluster.id)).where(Cluster.is_top)
    )
    assert top_count == 5
```

- [ ] **Step 2: Run, verify fails**

- [ ] **Step 3: Write `api/src/noticias_api/pipeline/rank.py`**

```python
import logging
import math
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Cluster

logger = logging.getLogger(__name__)

MIN_SOURCE_COUNT = 2


async def rank_top_clusters(session: AsyncSession, *, top_n: int) -> None:
    """Compute rank_score for clusters and mark top N as is_top with display_date=today."""
    today = date.today()
    now = datetime.now(UTC)

    candidates = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.source_count >= MIN_SOURCE_COUNT)
            .where(Cluster.last_seen_at.is_not(None))
        )
    ).all()

    scored: list[tuple[Cluster, float]] = []
    for c in candidates:
        last_seen = c.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        hours_ago = max(0.0, (now - last_seen).total_seconds() / 3600.0)
        score = c.source_count * 2 + math.log(c.article_count + 1) - hours_ago * 0.05
        scored.append((c, score))

    scored.sort(key=lambda t: t[1], reverse=True)

    # reset all is_top first
    await session.execute(update(Cluster).values(is_top=False))

    for cluster, score in scored[:top_n]:
        cluster.rank_score = score
        cluster.is_top = True
        cluster.display_date = today

    await session.commit()
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_rank.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/pipeline/rank.py api/tests/test_rank.py
git commit -m "feat(pipeline): rank clusters by sources × recency"
```

---

### Task 14: Pipeline step — analysis (GPT-4o)

**Files:**
- Create: `api/src/noticias_api/pipeline/analyze.py`
- Create: `api/src/noticias_api/pipeline/prompts.py`
- Create: `api/tests/test_analyze.py`

- [ ] **Step 1: Write `api/src/noticias_api/pipeline/prompts.py`**

```python
PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """\
Sos un analista de medios argentinos. Te paso N artículos del MISMO HECHO,
publicados por distintos diarios. Devolvé JSON con la siguiente estructura:

{
  "headline": "titular neutral, 12-15 palabras",
  "common_facts": ["hechos que TODOS reportan"],
  "by_source": {
    "<slug>": {
      "highlights": ["lo que ESTE diario destaca"],
      "framing": "cómo encuadra el hecho (1 oración)",
      "tone": "neutral|crítico|favorable|alarmista|otro"
    }
  },
  "omissions": [{"source": "<slug>", "not_mentioned": "qué hechos clave omite"}],
  "divergences": [
    {
      "topic": "punto en disputa",
      "positions": {"<slug>": "su postura/cita textual breve"}
    }
  ]
}

No inventes citas. Si un dato no está en el texto del diario, no lo atribuyas.
Devolvé únicamente JSON válido.
"""


def build_user_prompt(articles: list[dict]) -> str:
    """articles: list of {slug, title, body}"""
    parts = ["Diarios:\n"]
    for a in articles:
        parts.append(f"[{a['slug']}] {a['title']}\n{a['body']}\n")
    return "\n".join(parts)
```

- [ ] **Step 2: Write failing test `api/tests/test_analyze.py`**

```python
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from noticias_api.pipeline.analyze import AnalysisResult, analyze_cluster


def _mock_openai_response(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@pytest.mark.asyncio
async def test_analyze_cluster_parses_valid_json():
    payload = {
        "headline": "Inflación abril 4,2%",
        "common_facts": ["IPC 4,2%", "Acumulada 142%"],
        "by_source": {
            "la-nacion": {
                "highlights": ["destaca desaceleración"],
                "framing": "positivo para gobierno",
                "tone": "favorable",
            }
        },
        "omissions": [{"source": "la-nacion", "not_mentioned": "alimentos"}],
        "divergences": [{"topic": "causa", "positions": {"la-nacion": "X"}}],
    }
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(json.dumps(payload))
    )

    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "la-nacion", "title": "x", "body": "y"}],
        model="gpt-4o",
    )

    assert isinstance(result, AnalysisResult)
    assert result.headline == "Inflación abril 4,2%"
    assert "IPC 4,2%" in result.common_facts


@pytest.mark.asyncio
async def test_analyze_cluster_retries_on_invalid_json():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response("not json"),
            _mock_openai_response(json.dumps({
                "headline": "x",
                "common_facts": [],
                "by_source": {},
                "omissions": [],
                "divergences": [],
            })),
        ]
    )
    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "x", "title": "t", "body": "b"}],
        model="gpt-4o",
    )
    assert result.headline == "x"
    assert fake_client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_analyze_cluster_returns_none_after_two_failures():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("still not json")
    )
    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "x", "title": "t", "body": "b"}],
        model="gpt-4o",
    )
    assert result is None
```

- [ ] **Step 3: Run, verify fails**

- [ ] **Step 4: Write `api/src/noticias_api/pipeline/analyze.py`**

```python
import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from noticias_api.pipeline.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class BySource(BaseModel):
    highlights: list[str]
    framing: str
    tone: str


class Omission(BaseModel):
    source: str
    not_mentioned: str


class Divergence(BaseModel):
    topic: str
    positions: dict[str, str]


class AnalysisResult(BaseModel):
    headline: str
    common_facts: list[str]
    by_source: dict[str, BySource]
    omissions: list[Omission]
    divergences: list[Divergence]


async def _request(client: AsyncOpenAI, model: str, prompt: str, *, temperature: float) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def analyze_cluster(
    client: AsyncOpenAI,
    *,
    articles: list[dict[str, Any]],
    model: str,
) -> AnalysisResult | None:
    prompt = build_user_prompt(articles)
    for attempt, temp in enumerate([0.3, 0.0]):
        try:
            raw = await _request(client, model, prompt, temperature=temp)
            data = json.loads(raw)
            return AnalysisResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("analyze_cluster attempt %s failed: %s", attempt + 1, exc)
    return None


def prompt_version() -> str:
    return PROMPT_VERSION
```

- [ ] **Step 5: Run, verify pass**

```bash
pytest tests/test_analyze.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add api/src/noticias_api/pipeline/prompts.py api/src/noticias_api/pipeline/analyze.py api/tests/test_analyze.py
git commit -m "feat(pipeline): GPT-4o cluster analysis with JSON validation and retry"
```

---

## Phase 3: Pipeline orchestration

### Task 15: Pipeline runner

**Files:**
- Create: `api/src/noticias_api/pipeline/runner.py`
- Create: `api/tests/test_runner.py`

- [ ] **Step 1: Write failing test `api/tests/test_runner.py`**

```python
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from noticias_api.db.models import Article, Run, Source
from noticias_api.pipeline.runner import PipelineConfig, run_pipeline


@pytest.fixture
def pipeline_config():
    return PipelineConfig(
        top_n=15, similarity_threshold=0.78, window_hours=48,
        embedding_model="text-embedding-3-small",
        analysis_model="gpt-4o", user_agent="test",
    )


@pytest.mark.asyncio
async def test_run_pipeline_creates_run_row_and_marks_success(
    db_session, pipeline_config, monkeypatch
):
    src = Source(slug="t", name="Test", editorial_group="mainstream",
                 rss_url="https://t/rss", base_url="https://t", enabled=True)
    db_session.add(src)
    await db_session.commit()

    monkeypatch.setattr(
        "noticias_api.pipeline.runner._fetch_source_items",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._extract_for_articles",
        AsyncMock(return_value={"updated": 0}),
    )
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._embed_pending_articles",
        AsyncMock(return_value={"embedded": 0}),
    )
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._analyze_top_clusters",
        AsyncMock(return_value={"analyzed": 0}),
    )

    run_id = await run_pipeline(db_session, pipeline_config, trigger="manual")

    run = await db_session.get(Run, run_id)
    assert run.status == "success"
    assert run.trigger == "manual"
    assert run.finished_at is not None
    assert run.stats is not None


@pytest.mark.asyncio
async def test_run_pipeline_marks_failed_on_unhandled_error(
    db_session, pipeline_config, monkeypatch
):
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._fetch_source_items",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError):
        await run_pipeline(db_session, pipeline_config, trigger="cron")

    run = (await db_session.scalars(select(Run).order_by(Run.id.desc()))).first()
    assert run.status == "failed"
    assert "boom" in run.error
```

- [ ] **Step 2: Run, verify fails**

- [ ] **Step 3: Write `api/src/noticias_api/pipeline/runner.py`**

```python
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Run, Source
from noticias_api.pipeline.analyze import analyze_cluster, prompt_version
from noticias_api.pipeline.cluster import cluster_recent_articles
from noticias_api.pipeline.embed import build_embedding_input, embed_texts
from noticias_api.pipeline.extract import extract_content
from noticias_api.pipeline.fetch import fetch_feed, parse_feed
from noticias_api.pipeline.persist import persist_items
from noticias_api.pipeline.rank import rank_top_clusters

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    top_n: int
    similarity_threshold: float
    window_hours: int
    embedding_model: str
    analysis_model: str
    user_agent: str
    max_concurrent: int = 8


@dataclass
class RunStats:
    fetched: int = 0
    persisted: int = 0
    extracted: int = 0
    embedded: int = 0
    clustered: int = 0
    new_clusters: int = 0
    analyzed: int = 0
    errors_per_source: dict[str, int] = field(default_factory=dict)

    def dump(self) -> dict:
        return {
            "fetched": self.fetched,
            "persisted": self.persisted,
            "extracted": self.extracted,
            "embedded": self.embedded,
            "clustered": self.clustered,
            "new_clusters": self.new_clusters,
            "analyzed": self.analyzed,
            "errors_per_source": self.errors_per_source,
        }


async def run_pipeline(
    session: AsyncSession,
    cfg: PipelineConfig,
    *,
    trigger: str,
    openai_client: AsyncOpenAI | None = None,
) -> int:
    run = Run(trigger=trigger, status="running")
    session.add(run)
    await session.commit()
    run_id = run.id
    stats = RunStats()

    try:
        async with httpx.AsyncClient(headers={"User-Agent": cfg.user_agent}) as http:
            sources = (
                await session.scalars(select(Source).where(Source.enabled.is_(True)))
            ).all()

            for src in sources:
                try:
                    items = await _fetch_source_items(http, src, cfg)
                    stats.fetched += len(items)
                    inserted = await persist_items(session, src.id, items)
                    stats.persisted += inserted
                except Exception as exc:
                    logger.exception("fetch failed for %s", src.slug)
                    stats.errors_per_source[src.slug] = (
                        stats.errors_per_source.get(src.slug, 0) + 1
                    )

            extract_stats = await _extract_for_articles(session, http, cfg)
            stats.extracted = extract_stats.get("updated", 0)

            client = openai_client or AsyncOpenAI()
            embed_stats = await _embed_pending_articles(session, client, cfg)
            stats.embedded = embed_stats.get("embedded", 0)

            cluster_stats = await cluster_recent_articles(
                session, threshold=cfg.similarity_threshold, window_hours=cfg.window_hours
            )
            stats.clustered = cluster_stats.get("clustered", 0)
            stats.new_clusters = cluster_stats.get("new_clusters", 0)

            await rank_top_clusters(session, top_n=cfg.top_n)

            analyze_stats = await _analyze_top_clusters(session, client, cfg)
            stats.analyzed = analyze_stats.get("analyzed", 0)

        final_status = "partial" if stats.errors_per_source else "success"
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(status=final_status, finished_at=datetime.now(UTC), stats=stats.dump())
        )
        await session.commit()
        return run_id
    except Exception as exc:
        logger.exception("pipeline failed")
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                status="failed",
                finished_at=datetime.now(UTC),
                stats=stats.dump(),
                error=str(exc),
            )
        )
        await session.commit()
        raise


async def _fetch_source_items(http: httpx.AsyncClient, source: Source, cfg: PipelineConfig):
    cutoff = datetime.now(UTC) - timedelta(hours=cfg.window_hours)
    xml = await fetch_feed(http, source.rss_url)
    return parse_feed(xml, since=cutoff)


async def _extract_for_articles(
    session: AsyncSession, http: httpx.AsyncClient, cfg: PipelineConfig
) -> dict:
    pending = (
        await session.scalars(
            select(Article).where(Article.content.is_(None)).limit(200)
        )
    ).all()
    updated = 0
    for article in pending:
        result = await extract_content(http, article.url)
        article.content = result.content
        article.has_full_text = result.has_full_text
        updated += 1
    await session.commit()
    return {"updated": updated}


async def _embed_pending_articles(
    session: AsyncSession, client: AsyncOpenAI, cfg: PipelineConfig
) -> dict:
    pending = (
        await session.scalars(
            select(Article).where(Article.embedding.is_(None)).limit(500)
        )
    ).all()
    if not pending:
        return {"embedded": 0}
    inputs = [
        build_embedding_input(title=a.title, content=a.content, summary=a.summary)
        for a in pending
    ]
    vectors = await embed_texts(client, inputs, model=cfg.embedding_model)
    for article, vec in zip(pending, vectors, strict=True):
        article.embedding = vec
    await session.commit()
    return {"embedded": len(pending)}


async def _analyze_top_clusters(
    session: AsyncSession, client: AsyncOpenAI, cfg: PipelineConfig
) -> dict:
    clusters = (
        await session.scalars(
            select(Cluster).where(Cluster.is_top.is_(True))
        )
    ).all()
    analyzed = 0
    for cluster in clusters:
        existing = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == cluster.id)
        )
        if existing and existing.generated_at >= cluster.last_seen_at:
            continue
        articles = (
            await session.scalars(
                select(Article)
                .where(Article.cluster_id == cluster.id)
                .order_by(Article.published_at)
            )
        ).all()
        payload = []
        for art in articles:
            src = await session.get(Source, art.source_id)
            body = (art.content or art.summary or "")[:3000]
            payload.append({"slug": src.slug, "title": art.title, "body": body})
        result = await analyze_cluster(
            client, articles=payload, model=cfg.analysis_model
        )
        if result is None:
            continue
        if existing:
            existing.headline = result.headline
            existing.common_facts = result.common_facts
            existing.by_source = {k: v.model_dump() for k, v in result.by_source.items()}
            existing.omissions = [o.model_dump() for o in result.omissions]
            existing.divergences = [d.model_dump() for d in result.divergences]
            existing.model = cfg.analysis_model
            existing.prompt_version = prompt_version()
            existing.generated_at = datetime.now(UTC)
        else:
            session.add(
                Analysis(
                    cluster_id=cluster.id,
                    headline=result.headline,
                    common_facts=result.common_facts,
                    by_source={k: v.model_dump() for k, v in result.by_source.items()},
                    omissions=[o.model_dump() for o in result.omissions],
                    divergences=[d.model_dump() for d in result.divergences],
                    model=cfg.analysis_model,
                    prompt_version=prompt_version(),
                )
            )
        analyzed += 1
    await session.commit()
    return {"analyzed": analyzed}
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_runner.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/src/noticias_api/pipeline/runner.py api/tests/test_runner.py
git commit -m "feat(pipeline): runner orchestrating all 8 steps with run row tracking"
```

---

### Task 16: Scheduler, refresh endpoint, run polling

**Files:**
- Create: `api/src/noticias_api/scheduler.py`
- Create: `api/src/noticias_api/api/runs.py`
- Modify: `api/src/noticias_api/main.py`
- Create: `api/tests/test_runs_api.py`

- [ ] **Step 1: Write `api/src/noticias_api/scheduler.py`**

```python
import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI

from noticias_api.config import Settings
from noticias_api.db.session import async_session_factory
from noticias_api.pipeline.runner import PipelineConfig, run_pipeline

logger = logging.getLogger(__name__)

_pipeline_lock = asyncio.Lock()
_current_run_id: int | None = None


def get_current_run_id() -> int | None:
    return _current_run_id


async def _run_locked(trigger: str, settings: Settings) -> int:
    global _current_run_id
    async with _pipeline_lock:
        cfg = PipelineConfig(
            top_n=settings.top_n_clusters,
            similarity_threshold=settings.similarity_threshold,
            window_hours=settings.cluster_window_hours,
            embedding_model=settings.embedding_model,
            analysis_model=settings.chat_model_analysis,
            user_agent=settings.user_agent,
            max_concurrent=settings.max_concurrent_fetches,
        )
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        async with async_session_factory() as session:
            run_id = await run_pipeline(
                session, cfg, trigger=trigger, openai_client=client
            )
            _current_run_id = run_id
            return run_id


def schedule_pipeline_in_task(trigger: str, settings: Settings) -> asyncio.Task:
    return asyncio.create_task(_run_locked(trigger, settings))


def setup_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(
        lambda: asyncio.create_task(_run_locked("cron", settings)),
        CronTrigger(hour=settings.cron_hour, minute=settings.cron_minute),
        id="daily_briefing",
        replace_existing=True,
    )
    return scheduler


def is_pipeline_running() -> bool:
    return _pipeline_lock.locked()
```

- [ ] **Step 2: Write failing test `api/tests/test_runs_api.py`**

```python
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from noticias_api.db.models import Run


def test_post_refresh_returns_202_with_run_id(client, monkeypatch):
    async def fake_run_locked(trigger, settings):
        return 42

    monkeypatch.setattr(
        "noticias_api.api.runs._run_locked", fake_run_locked
    )
    monkeypatch.setattr(
        "noticias_api.api.runs.is_pipeline_running", lambda: False
    )

    response = client.post("/refresh")
    assert response.status_code == 202
    assert "run_id" in response.json()
    assert response.json()["status"] == "queued"


def test_post_refresh_returns_409_when_already_running(client, monkeypatch):
    monkeypatch.setattr("noticias_api.api.runs.is_pipeline_running", lambda: True)
    monkeypatch.setattr("noticias_api.api.runs.get_current_run_id", lambda: 99)

    response = client.post("/refresh")
    assert response.status_code == 409
    assert response.json()["run_id"] == 99


@pytest.mark.asyncio
async def test_get_run_returns_status(db_session, client):
    run = Run(trigger="manual", status="success")
    db_session.add(run)
    await db_session.commit()

    response = client.get(f"/runs/{run.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run.id
    assert body["status"] == "success"


def test_get_run_404(client):
    response = client.get("/runs/999999")
    assert response.status_code == 404
```

- [ ] **Step 3: Run, verify fails**

- [ ] **Step 4: Write `api/src/noticias_api/api/runs.py`**

```python
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.models import Run
from noticias_api.db.session import get_session
from noticias_api.scheduler import (
    _run_locked,
    get_current_run_id,
    is_pipeline_running,
)

router = APIRouter(tags=["runs"])


class RunOut(BaseModel):
    id: int
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    stats: dict | None
    error: str | None


class RefreshResponse(BaseModel):
    run_id: int
    status: str


@router.post("/refresh", status_code=202, response_model=RefreshResponse)
async def trigger_refresh(settings: Settings = Depends(get_settings)) -> RefreshResponse:
    if is_pipeline_running():
        existing = get_current_run_id()
        raise HTTPException(
            status_code=409,
            detail={"run_id": existing, "status": "running"},
        )
    task = asyncio.create_task(_run_locked("manual", settings))
    # we cannot await here; immediately return queued. The run_id will be set
    # by _run_locked once the Run row is created.
    # For simplicity, we report run_id=0 + status=queued; the client polls
    # /runs/latest or uses the current_run_id endpoint.
    return RefreshResponse(run_id=0, status="queued")


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: int, session: AsyncSession = Depends(get_session)) -> Run:
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs", response_model=list[RunOut])
async def list_runs(
    limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[Run]:
    rows = await session.scalars(select(Run).order_by(Run.id.desc()).limit(limit))
    return list(rows.all())


@router.get("/runs/current", response_model=RunOut | None)
async def current_run(session: AsyncSession = Depends(get_session)) -> Run | None:
    run_id = get_current_run_id()
    if run_id is None:
        return None
    return await session.get(Run, run_id)
```

- [ ] **Step 5: Update `api/src/noticias_api/main.py`**

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from noticias_api.api import runs, sources
from noticias_api.config import get_settings
from noticias_api.scheduler import setup_scheduler

logging.basicConfig(level=get_settings().log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    scheduler = setup_scheduler(settings)
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Noticias API", version="0.1.0", lifespan=lifespan)
app.include_router(sources.router)
app.include_router(runs.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run tests, verify pass**

```bash
pytest tests/test_runs_api.py -v
```

Expected: 4 PASSED.

- [ ] **Step 7: Commit**

```bash
git add api/src/noticias_api/scheduler.py api/src/noticias_api/api/runs.py api/src/noticias_api/main.py api/tests/test_runs_api.py
git commit -m "feat(api): scheduler, POST /refresh, GET /runs endpoints"
```

---

## Phase 4: Read API endpoints

### Task 17: Briefings endpoints

**Files:**
- Create: `api/src/noticias_api/api/briefings.py`
- Modify: `api/src/noticias_api/main.py`
- Create: `api/tests/test_briefings_api.py`

- [ ] **Step 1: Write failing test `api/tests/test_briefings_api.py`**

```python
from datetime import UTC, date, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.seed import seed_sources


@pytest.mark.asyncio
async def test_get_today_briefing_returns_top_clusters_only(db_session, client):
    await seed_sources(db_session)
    today = date.today()
    now = datetime.now(UTC)

    top = Cluster(
        article_count=4, source_count=4, last_seen_at=now,
        rank_score=10.0, is_top=True, display_date=today,
    )
    not_top = Cluster(
        article_count=1, source_count=1, last_seen_at=now,
        rank_score=1.0, is_top=False, display_date=today,
    )
    db_session.add_all([top, not_top])
    await db_session.commit()

    db_session.add(Analysis(
        cluster_id=top.id, headline="Test headline",
        common_facts=["a", "b"], by_source={}, omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v1",
    ))
    await db_session.commit()

    response = client.get("/briefings/today")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == today.isoformat()
    assert len(body["clusters"]) == 1
    assert body["clusters"][0]["headline"] == "Test headline"


@pytest.mark.asyncio
async def test_get_briefing_by_date(db_session, client):
    await seed_sources(db_session)
    target = date(2026, 4, 1)
    now = datetime.now(UTC)
    c = Cluster(article_count=3, source_count=3, last_seen_at=now,
                rank_score=5.0, is_top=True, display_date=target)
    db_session.add(c)
    await db_session.commit()

    response = client.get(f"/briefings/{target.isoformat()}")
    assert response.status_code == 200
    assert len(response.json()["clusters"]) == 1


@pytest.mark.asyncio
async def test_list_briefing_dates(db_session, client):
    now = datetime.now(UTC)
    for d in [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)]:
        c = Cluster(article_count=2, source_count=2, last_seen_at=now,
                    rank_score=1.0, is_top=True, display_date=d)
        db_session.add(c)
    await db_session.commit()

    response = client.get("/briefings")
    assert response.status_code == 200
    dates = response.json()
    assert len(dates) == 3
    assert dates[0] == "2026-05-03"  # newest first
```

- [ ] **Step 2: Run, verify fails**

- [ ] **Step 3: Write `api/src/noticias_api/api/briefings.py`**

```python
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["briefings"])


class ClusterSummary(BaseModel):
    id: int
    headline: str | None
    source_count: int
    article_count: int
    sources: list[str]
    rank_score: float | None
    common_facts: list[str]
    divergence_count: int


class BriefingOut(BaseModel):
    date: date
    generated_at: datetime | None
    clusters: list[ClusterSummary]


async def _build_briefing(session: AsyncSession, target: date) -> BriefingOut:
    clusters = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.is_top.is_(True))
            .where(Cluster.display_date == target)
            .order_by(Cluster.rank_score.desc().nullslast())
        )
    ).all()

    summaries: list[ClusterSummary] = []
    generated_at: datetime | None = None

    for c in clusters:
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == c.id)
        )
        article_sources = (
            await session.scalars(
                select(Source.slug)
                .join(Article, Article.source_id == Source.id)
                .where(Article.cluster_id == c.id)
                .distinct()
            )
        ).all()
        summaries.append(
            ClusterSummary(
                id=c.id,
                headline=analysis.headline if analysis else None,
                source_count=c.source_count,
                article_count=c.article_count,
                sources=list(article_sources),
                rank_score=c.rank_score,
                common_facts=analysis.common_facts if analysis else [],
                divergence_count=len(analysis.divergences) if analysis else 0,
            )
        )
        if analysis and (generated_at is None or analysis.generated_at > generated_at):
            generated_at = analysis.generated_at

    return BriefingOut(date=target, generated_at=generated_at, clusters=summaries)


@router.get("/briefings/today", response_model=BriefingOut)
async def get_today(session: AsyncSession = Depends(get_session)) -> BriefingOut:
    return await _build_briefing(session, date.today())


@router.get("/briefings/{target_date}", response_model=BriefingOut)
async def get_by_date(
    target_date: date, session: AsyncSession = Depends(get_session)
) -> BriefingOut:
    return await _build_briefing(session, target_date)


@router.get("/briefings", response_model=list[date])
async def list_dates(session: AsyncSession = Depends(get_session)) -> list[date]:
    rows = await session.scalars(
        select(distinct(Cluster.display_date))
        .where(Cluster.is_top.is_(True))
        .where(Cluster.display_date.is_not(None))
        .order_by(Cluster.display_date.desc())
    )
    return [d for d in rows.all() if d is not None]
```

- [ ] **Step 4: Wire router in `api/src/noticias_api/main.py`**

Add to imports:

```python
from noticias_api.api import briefings, runs, sources
```

Add after `app.include_router(runs.router)`:

```python
app.include_router(briefings.router)
```

- [ ] **Step 5: Run, verify pass**

```bash
pytest tests/test_briefings_api.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add api/src/noticias_api/api/briefings.py api/src/noticias_api/main.py api/tests/test_briefings_api.py
git commit -m "feat(api): briefings endpoints (today, by date, list dates)"
```

---

### Task 18: Cluster detail endpoint

**Files:**
- Create: `api/src/noticias_api/api/clusters.py`
- Modify: `api/src/noticias_api/main.py`
- Create: `api/tests/test_clusters_api.py`

- [ ] **Step 1: Write failing test `api/tests/test_clusters_api.py`**

```python
from datetime import UTC, datetime

import pytest

from noticias_api.db.models import Analysis, Article, Cluster, Source


@pytest.mark.asyncio
async def test_get_cluster_returns_full_detail(db_session, client):
    src = Source(slug="ln", name="LN", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()

    cluster = Cluster(article_count=1, source_count=1, last_seen_at=datetime.now(UTC))
    db_session.add(cluster)
    await db_session.commit()

    art = Article(
        source_id=src.id, external_id="a1", url="https://ln/a1",
        title="Inflación abril", summary="resumen", content="contenido completo",
        has_full_text=True, published_at=datetime.now(UTC), cluster_id=cluster.id,
    )
    db_session.add(art)

    db_session.add(Analysis(
        cluster_id=cluster.id, headline="Inflación abril 4,2%",
        common_facts=["IPC 4,2%"],
        by_source={"ln": {"highlights": ["x"], "framing": "y", "tone": "neutral"}},
        omissions=[], divergences=[],
        model="gpt-4o", prompt_version="v1",
    ))
    await db_session.commit()

    response = client.get(f"/clusters/{cluster.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == cluster.id
    assert body["analysis"]["headline"] == "Inflación abril 4,2%"
    assert len(body["articles"]) == 1
    assert body["articles"][0]["source"]["slug"] == "ln"


def test_get_cluster_404(client):
    response = client.get("/clusters/999999")
    assert response.status_code == 404
```

- [ ] **Step 2: Run, verify fails**

- [ ] **Step 3: Write `api/src/noticias_api/api/clusters.py`**

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Analysis, Article, Cluster, Source
from noticias_api.db.session import get_session

router = APIRouter(tags=["clusters"])


class SourceRef(BaseModel):
    slug: str
    name: str
    editorial_group: str


class ArticleOut(BaseModel):
    id: int
    source: SourceRef
    title: str
    url: str
    summary: str | None
    has_full_text: bool
    published_at: datetime | None


class AnalysisOut(BaseModel):
    headline: str | None
    common_facts: list[str]
    by_source: dict
    omissions: list[dict]
    divergences: list[dict]
    model: str | None
    prompt_version: str | None
    generated_at: datetime


class ClusterDetail(BaseModel):
    id: int
    first_seen_at: datetime
    last_seen_at: datetime
    article_count: int
    source_count: int
    analysis: AnalysisOut | None
    articles: list[ArticleOut]


@router.get("/clusters/{cluster_id}", response_model=ClusterDetail)
async def get_cluster(
    cluster_id: int, session: AsyncSession = Depends(get_session)
) -> ClusterDetail:
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="cluster not found")

    analysis = await session.scalar(
        select(Analysis).where(Analysis.cluster_id == cluster_id)
    )
    articles = (
        await session.scalars(
            select(Article)
            .where(Article.cluster_id == cluster_id)
            .order_by(Article.published_at)
        )
    ).all()

    article_outs: list[ArticleOut] = []
    for art in articles:
        src = await session.get(Source, art.source_id)
        article_outs.append(
            ArticleOut(
                id=art.id,
                source=SourceRef(
                    slug=src.slug, name=src.name, editorial_group=src.editorial_group
                ),
                title=art.title,
                url=art.url,
                summary=art.summary,
                has_full_text=art.has_full_text,
                published_at=art.published_at,
            )
        )

    analysis_out: AnalysisOut | None = None
    if analysis:
        analysis_out = AnalysisOut(
            headline=analysis.headline,
            common_facts=analysis.common_facts or [],
            by_source=analysis.by_source or {},
            omissions=analysis.omissions or [],
            divergences=analysis.divergences or [],
            model=analysis.model,
            prompt_version=analysis.prompt_version,
            generated_at=analysis.generated_at,
        )

    return ClusterDetail(
        id=cluster.id,
        first_seen_at=cluster.first_seen_at,
        last_seen_at=cluster.last_seen_at,
        article_count=cluster.article_count,
        source_count=cluster.source_count,
        analysis=analysis_out,
        articles=article_outs,
    )
```

- [ ] **Step 4: Wire in `api/src/noticias_api/main.py`**

Update imports:

```python
from noticias_api.api import briefings, clusters, runs, sources
```

Add:

```python
app.include_router(clusters.router)
```

- [ ] **Step 5: Run, verify pass**

```bash
pytest tests/test_clusters_api.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Run all API tests as smoke check**

```bash
pytest tests/ -v
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add api/src/noticias_api/api/clusters.py api/src/noticias_api/main.py api/tests/test_clusters_api.py
git commit -m "feat(api): GET /clusters/:id with full analysis and articles"
```

---

## Phase 5: Web foundation

### Task 19: Next.js scaffolding

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/postcss.config.mjs`
- Create: `web/Dockerfile`
- Create: `web/.dockerignore`
- Create: `web/app/globals.css`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/providers.tsx`

- [ ] **Step 1: Write `web/package.json`**

```json
{
  "name": "noticias-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "playwright test"
  },
  "dependencies": {
    "next": "15.1.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "next-themes": "^0.4.4"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@playwright/test": "^1.49.0",
    "@tailwindcss/postcss": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0"
  },
  "packageManager": "pnpm@9.15.0"
}
```

- [ ] **Step 2: Write `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": { "@/*": ["./*"] },
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Write `web/next.config.ts`**

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 4: Write `web/postcss.config.mjs`**

```js
export default {
  plugins: { "@tailwindcss/postcss": {} },
};
```

- [ ] **Step 5: Write `web/app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-mainstream-bg: oklch(0.97 0.01 80);
  --color-mainstream-fg: oklch(0.30 0.03 80);
  --color-critico-bg: oklch(0.96 0.02 250);
  --color-critico-fg: oklch(0.30 0.05 250);
  --color-economico-bg: oklch(0.97 0.02 140);
  --color-economico-fg: oklch(0.30 0.05 140);
  --font-serif: ui-serif, Georgia, Cambria, "Times New Roman", serif;
  --font-sans: system-ui, -apple-system, sans-serif;
}

html { color-scheme: light dark; }
body { font-family: var(--font-sans); }
h1, h2, h3 { font-family: var(--font-serif); }
```

- [ ] **Step 6: Write `web/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Noticias",
  description: "Comparador de coberturas de diarios argentinos",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="bg-white text-stone-900 dark:bg-stone-950 dark:text-stone-100">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 7: Write `web/app/providers.tsx`**

```tsx
"use client";

import { ThemeProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

- [ ] **Step 8: Write placeholder `web/app/page.tsx`**

```tsx
export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-3xl">Noticias</h1>
      <p className="mt-2 text-stone-600 dark:text-stone-400">Briefing del día</p>
    </main>
  );
}
```

- [ ] **Step 9: Write `web/Dockerfile`**

```dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile || pnpm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 10: Write `web/.dockerignore`**

```
node_modules
.next
.pnpm-store
.git
```

- [ ] **Step 11: Install and run dev server**

```bash
cd web && pnpm install
pnpm dev
```

Visit http://localhost:3000 — should show "Noticias / Briefing del día".

```bash
# stop with Ctrl+C
```

- [ ] **Step 12: Commit**

```bash
git add web/
git commit -m "feat(web): scaffold Next.js 15 app with Tailwind 4 and theme provider"
```

---

### Task 20: API client and shared types

**Files:**
- Create: `web/lib/api.ts`
- Create: `web/lib/types.ts`

- [ ] **Step 1: Write `web/lib/types.ts`**

```ts
export type EditorialGroup = "mainstream" | "critico" | "economico";

export interface SourceRef {
  slug: string;
  name: string;
  editorial_group: EditorialGroup;
}

export interface ClusterSummary {
  id: number;
  headline: string | null;
  source_count: number;
  article_count: number;
  sources: string[];
  rank_score: number | null;
  common_facts: string[];
  divergence_count: number;
}

export interface Briefing {
  date: string;
  generated_at: string | null;
  clusters: ClusterSummary[];
}

export interface ArticleDetail {
  id: number;
  source: SourceRef;
  title: string;
  url: string;
  summary: string | null;
  has_full_text: boolean;
  published_at: string | null;
}

export interface BySourceAnalysis {
  highlights: string[];
  framing: string;
  tone: string;
}

export interface Omission {
  source: string;
  not_mentioned: string;
}

export interface Divergence {
  topic: string;
  positions: Record<string, string>;
}

export interface AnalysisDetail {
  headline: string | null;
  common_facts: string[];
  by_source: Record<string, BySourceAnalysis>;
  omissions: Omission[];
  divergences: Divergence[];
  model: string | null;
  prompt_version: string | null;
  generated_at: string;
}

export interface ClusterDetail {
  id: number;
  first_seen_at: string;
  last_seen_at: string;
  article_count: number;
  source_count: number;
  analysis: AnalysisDetail | null;
  articles: ArticleDetail[];
}

export interface SourceListItem {
  slug: string;
  name: string;
  editorial_group: EditorialGroup;
  rss_url: string;
  base_url: string;
  enabled: boolean;
}

export interface RunDetail {
  id: number;
  trigger: "cron" | "manual";
  status: "queued" | "running" | "success" | "partial" | "failed";
  started_at: string;
  finished_at: string | null;
  stats: Record<string, unknown> | null;
  error: string | null;
}
```

- [ ] **Step 2: Write `web/lib/api.ts`**

```ts
import {
  Briefing,
  ClusterDetail,
  RunDetail,
  SourceListItem,
} from "./types";

const baseUrl = (): string => {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_URL ?? "http://api:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
};

async function get<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...opts?.headers },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getTodayBriefing: (): Promise<Briefing> =>
    get("/briefings/today", { next: { revalidate: 60 } }),
  getBriefingByDate: (date: string): Promise<Briefing> =>
    get(`/briefings/${date}`, { next: { revalidate: 60 } }),
  listBriefingDates: (): Promise<string[]> =>
    get("/briefings", { next: { revalidate: 300 } }),
  getCluster: (id: number): Promise<ClusterDetail> =>
    get(`/clusters/${id}`, { next: { revalidate: 300 } }),
  getSources: (): Promise<SourceListItem[]> =>
    get("/sources", { next: { revalidate: 300 } }),
  getRun: (id: number): Promise<RunDetail> => get(`/runs/${id}`, { cache: "no-store" }),
};
```

- [ ] **Step 3: Commit**

```bash
git add web/lib/
git commit -m "feat(web): API client and shared TypeScript types"
```

---

### Task 21: Layout shell

**Files:**
- Create: `web/components/Header.tsx`
- Create: `web/components/Footer.tsx`
- Modify: `web/app/layout.tsx`

- [ ] **Step 1: Write `web/components/Header.tsx`**

```tsx
import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/85 backdrop-blur dark:border-stone-800 dark:bg-stone-950/85">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-xl font-serif font-bold tracking-tight">
          Noticias
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/historial" className="hover:underline">Historial</Link>
          <Link href="/fuentes" className="hover:underline">Fuentes</Link>
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Write `web/components/Footer.tsx`**

```tsx
export function Footer({ generatedAt }: { generatedAt?: string | null }) {
  return (
    <footer className="border-t border-stone-200 px-6 py-6 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-400">
      <div className="mx-auto max-w-5xl">
        {generatedAt && <p>Briefing generado: {new Date(generatedAt).toLocaleString("es-AR")}</p>}
        <p className="mt-1">Comparador de coberturas · Análisis con GPT-4o</p>
      </div>
    </footer>
  );
}
```

- [ ] **Step 3: Update `web/app/layout.tsx` to use Header**

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Noticias",
  description: "Comparador de coberturas de diarios argentinos",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen bg-white text-stone-900 dark:bg-stone-950 dark:text-stone-100">
        <Providers>
          <Header />
          {children}
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd web && pnpm build
```

Expected: builds without errors.

- [ ] **Step 5: Commit**

```bash
git add web/components/ web/app/layout.tsx
git commit -m "feat(web): header, footer, layout shell"
```

---

## Phase 6: Web pages

### Task 22: Home page (briefing of today) + ClusterCard

**Files:**
- Create: `web/components/SourceChip.tsx`
- Create: `web/components/ClusterCard.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Write `web/components/SourceChip.tsx`**

```tsx
import { EditorialGroup } from "@/lib/types";

const groupClass: Record<EditorialGroup, string> = {
  mainstream: "bg-mainstream-bg text-mainstream-fg",
  critico: "bg-critico-bg text-critico-fg",
  economico: "bg-economico-bg text-economico-fg",
};

export function SourceChip({
  slug,
  group,
}: {
  slug: string;
  group: EditorialGroup;
}) {
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${groupClass[group]}`}
    >
      {slug}
    </span>
  );
}
```

- [ ] **Step 2: Write `web/components/ClusterCard.tsx`**

```tsx
import Link from "next/link";

import { ClusterSummary, EditorialGroup, SourceListItem } from "@/lib/types";
import { SourceChip } from "./SourceChip";

interface Props {
  cluster: ClusterSummary;
  sourcesById: Map<string, SourceListItem>;
}

export function ClusterCard({ cluster, sourcesById }: Props) {
  return (
    <Link
      href={`/cluster/${cluster.id}`}
      className="block rounded-lg border border-stone-200 bg-white p-5 transition hover:border-stone-400 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-600"
    >
      <h2 className="text-xl font-serif leading-snug">
        {cluster.headline ?? "Análisis pendiente"}
      </h2>
      <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
        {cluster.source_count} {cluster.source_count === 1 ? "diario" : "diarios"} ·{" "}
        {cluster.divergence_count}{" "}
        {cluster.divergence_count === 1 ? "punto de divergencia" : "puntos de divergencia"}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {cluster.sources.map((slug) => {
          const src = sourcesById.get(slug);
          if (!src) return null;
          return (
            <SourceChip
              key={slug}
              slug={slug}
              group={src.editorial_group as EditorialGroup}
            />
          );
        })}
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Write `web/app/page.tsx`**

```tsx
import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";
import { RefreshButton } from "@/components/RefreshButton";

export const revalidate = 60;

export default async function HomePage() {
  const [briefing, sources] = await Promise.all([
    api.getTodayBriefing(),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-serif font-bold">Briefing del día</h1>
            <p className="mt-1 text-stone-600 dark:text-stone-400">
              {new Date(briefing.date).toLocaleDateString("es-AR", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
          <RefreshButton />
        </div>

        {briefing.clusters.length === 0 ? (
          <p className="mt-8 rounded-md border border-dashed border-stone-300 p-6 text-center text-stone-600 dark:border-stone-700 dark:text-stone-400">
            Briefing no generado todavía. Tocá <strong>Actualizar</strong> para correr el pipeline.
          </p>
        ) : (
          <ul className="mt-6 grid gap-4 md:grid-cols-2">
            {briefing.clusters.map((c) => (
              <li key={c.id}>
                <ClusterCard cluster={c} sourcesById={sourcesById} />
              </li>
            ))}
          </ul>
        )}
      </main>
      <Footer generatedAt={briefing.generated_at} />
    </>
  );
}
```

(`RefreshButton` will be created in Task 27. Until then, replace `<RefreshButton />` with a placeholder div or comment out the import.)

For now, use a placeholder. Replace `import { RefreshButton } from "@/components/RefreshButton";` and the `<RefreshButton />` usage temporarily with:

```tsx
// import { RefreshButton } from "@/components/RefreshButton"; // wired in Task 27
```

```tsx
{/* RefreshButton goes here in Task 27 */}
```

- [ ] **Step 4: Verify build (with placeholder)**

```bash
cd web && pnpm build
```

- [ ] **Step 5: Commit**

```bash
git add web/components/SourceChip.tsx web/components/ClusterCard.tsx web/app/page.tsx
git commit -m "feat(web): home page with briefing list and ClusterCard"
```

---

### Task 23: Cluster detail page + DivergenceTable

**Files:**
- Create: `web/components/DivergenceTable.tsx`
- Create: `web/components/SourceTabs.tsx`
- Create: `web/app/cluster/[id]/page.tsx`

- [ ] **Step 1: Write `web/components/DivergenceTable.tsx`**

```tsx
import { Divergence } from "@/lib/types";

export function DivergenceTable({ divergences }: { divergences: Divergence[] }) {
  if (divergences.length === 0) {
    return (
      <p className="text-sm text-stone-500 dark:text-stone-400">
        No se detectaron divergencias significativas entre las coberturas.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-stone-300 dark:border-stone-700">
            <th className="py-2 pr-4 text-left font-medium">Tema en disputa</th>
            <th className="py-2 text-left font-medium">Posiciones</th>
          </tr>
        </thead>
        <tbody>
          {divergences.map((d, i) => (
            <tr key={i} className="border-b border-stone-200 align-top dark:border-stone-800">
              <td className="py-3 pr-4 font-medium">{d.topic}</td>
              <td className="py-3">
                <ul className="space-y-1">
                  {Object.entries(d.positions).map(([slug, stance]) => (
                    <li key={slug}>
                      <span className="font-mono text-xs text-stone-500">{slug}:</span>{" "}
                      <span>{stance}</span>
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Write `web/components/SourceTabs.tsx`**

```tsx
"use client";

import { useState } from "react";

import { BySourceAnalysis, EditorialGroup, SourceListItem } from "@/lib/types";

interface Props {
  bySource: Record<string, BySourceAnalysis>;
  sourcesById: Map<string, SourceListItem>;
}

const groupBg: Record<EditorialGroup, string> = {
  mainstream: "bg-mainstream-bg",
  critico: "bg-critico-bg",
  economico: "bg-economico-bg",
};

export function SourceTabs({ bySource, sourcesById }: Props) {
  const slugs = Object.keys(bySource);
  const [active, setActive] = useState(slugs[0] ?? "");
  if (slugs.length === 0) return null;

  const data = bySource[active];
  const src = sourcesById.get(active);
  const group = (src?.editorial_group ?? "mainstream") as EditorialGroup;

  return (
    <div>
      <div className="flex flex-wrap gap-1 border-b border-stone-200 dark:border-stone-800">
        {slugs.map((slug) => (
          <button
            key={slug}
            type="button"
            onClick={() => setActive(slug)}
            className={`px-3 py-2 text-sm font-medium ${
              active === slug
                ? "border-b-2 border-stone-900 text-stone-900 dark:border-stone-100 dark:text-stone-100"
                : "text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
            }`}
          >
            {sourcesById.get(slug)?.name ?? slug}
          </button>
        ))}
      </div>
      <div className={`mt-4 rounded-md p-4 ${groupBg[group]}`}>
        <p className="text-xs uppercase tracking-wide opacity-70">Tono: {data.tone}</p>
        <p className="mt-2 text-sm italic">{data.framing}</p>
        <ul className="mt-3 list-inside list-disc text-sm">
          {data.highlights.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write `web/app/cluster/[id]/page.tsx`**

```tsx
import Link from "next/link";
import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { DivergenceTable } from "@/components/DivergenceTable";
import { Footer } from "@/components/Footer";
import { SourceChip } from "@/components/SourceChip";
import { SourceTabs } from "@/components/SourceTabs";

export const revalidate = 300;

export default async function ClusterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const clusterId = Number(id);
  if (!Number.isInteger(clusterId)) notFound();

  const [cluster, sources] = await Promise.all([
    api.getCluster(clusterId),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-4xl space-y-8 px-6 py-8">
        <header>
          <Link href="/" className="text-sm text-stone-500 hover:underline">
            ← Volver al briefing
          </Link>
          <h1 className="mt-2 text-3xl font-serif font-bold">
            {cluster.analysis?.headline ?? "Análisis pendiente"}
          </h1>
          <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
            {cluster.source_count} diarios · {cluster.article_count} artículos
          </p>
        </header>

        {cluster.analysis === null ? (
          <p className="rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
            El análisis para este cluster aún no se generó o falló. Tocá Actualizar para reintentar.
          </p>
        ) : (
          <>
            <section>
              <h2 className="text-xl font-serif font-semibold">Hechos en común</h2>
              <ul className="mt-3 list-inside list-disc space-y-1 text-sm">
                {cluster.analysis.common_facts.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Por diario</h2>
              <div className="mt-3">
                <SourceTabs
                  bySource={cluster.analysis.by_source}
                  sourcesById={sourcesById}
                />
              </div>
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Omisiones</h2>
              {cluster.analysis.omissions.length === 0 ? (
                <p className="mt-3 text-sm text-stone-500 dark:text-stone-400">
                  No se detectaron omisiones relevantes.
                </p>
              ) : (
                <ul className="mt-3 list-inside list-disc space-y-1 text-sm">
                  {cluster.analysis.omissions.map((o, i) => (
                    <li key={i}>
                      <strong className="font-mono text-xs">{o.source}</strong>{" "}
                      omite: {o.not_mentioned}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Divergencias</h2>
              <div className="mt-3">
                <DivergenceTable divergences={cluster.analysis.divergences} />
              </div>
            </section>
          </>
        )}

        <section>
          <h2 className="text-xl font-serif font-semibold">Artículos fuente</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {cluster.articles.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2">
                <SourceChip
                  slug={a.source.slug}
                  group={a.source.editorial_group}
                />
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  {a.title}
                </a>
                {!a.has_full_text && (
                  <span className="text-xs text-stone-500">(solo título/resumen)</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      </main>
      <Footer generatedAt={cluster.analysis?.generated_at ?? null} />
    </>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd web && pnpm build
```

- [ ] **Step 5: Commit**

```bash
git add web/components/DivergenceTable.tsx web/components/SourceTabs.tsx web/app/cluster/
git commit -m "feat(web): cluster detail page with tabs, divergence table, articles"
```

---

### Task 24: Historial page

**Files:**
- Create: `web/app/historial/page.tsx`

- [ ] **Step 1: Write `web/app/historial/page.tsx`**

```tsx
import Link from "next/link";

import { api } from "@/lib/api";

export const revalidate = 300;

export default async function HistorialPage() {
  const dates = await api.listBriefingDates();

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Historial de briefings</h1>
      {dates.length === 0 ? (
        <p className="mt-6 text-stone-600 dark:text-stone-400">
          Todavía no hay briefings generados.
        </p>
      ) : (
        <ul className="mt-6 space-y-2">
          {dates.map((date) => (
            <li key={date}>
              <Link
                href={`/briefing/${date}`}
                className="block rounded-md border border-stone-200 px-4 py-3 transition hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
              >
                {new Date(date).toLocaleDateString("es-AR", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Create `web/app/briefing/[date]/page.tsx`**

```tsx
import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";

export const revalidate = 60;

export default async function BriefingByDatePage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const [briefing, sources] = await Promise.all([
    api.getBriefingByDate(date),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="text-3xl font-serif font-bold">
          Briefing del{" "}
          {new Date(briefing.date).toLocaleDateString("es-AR", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </h1>
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {briefing.clusters.map((c) => (
            <li key={c.id}>
              <ClusterCard cluster={c} sourcesById={sourcesById} />
            </li>
          ))}
        </ul>
      </main>
      <Footer generatedAt={briefing.generated_at} />
    </>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd web && pnpm build
```

- [ ] **Step 4: Commit**

```bash
git add web/app/historial/ web/app/briefing/
git commit -m "feat(web): historial page and briefing by date"
```

---

### Task 25: Fuentes page (with toggle)

**Files:**
- Create: `web/app/fuentes/page.tsx`
- Create: `web/components/SourceToggle.tsx`
- Create: `web/app/api/sources/[slug]/route.ts`

- [ ] **Step 1: Write `web/app/api/sources/[slug]/route.ts` (proxy PATCH)**

```ts
import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const body = await req.text();
  const res = await fetch(`${INTERNAL}/sources/${slug}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

- [ ] **Step 2: Write `web/components/SourceToggle.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function SourceToggle({
  slug,
  enabled: initial,
}: {
  slug: string;
  enabled: boolean;
}) {
  const [enabled, setEnabled] = useState(initial);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function toggle() {
    setLoading(true);
    const next = !enabled;
    try {
      const res = await fetch(`/api/sources/${slug}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: next }),
      });
      if (res.ok) {
        setEnabled(next);
        router.refresh();
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={loading}
      className={`rounded-md px-3 py-1 text-sm font-medium transition ${
        enabled
          ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100"
          : "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400"
      } disabled:opacity-50`}
    >
      {enabled ? "Activo" : "Apagado"}
    </button>
  );
}
```

- [ ] **Step 3: Write `web/app/fuentes/page.tsx`**

```tsx
import { api } from "@/lib/api";
import { SourceToggle } from "@/components/SourceToggle";

export const revalidate = 0;

const groupLabel: Record<string, string> = {
  mainstream: "Mainstream",
  critico: "Crítico",
  economico: "Económico",
};

export default async function FuentesPage() {
  const sources = await api.getSources();
  const groups = sources.reduce<Record<string, typeof sources>>((acc, s) => {
    (acc[s.editorial_group] ??= []).push(s);
    return acc;
  }, {});

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Fuentes</h1>
      {Object.entries(groups).map(([group, items]) => (
        <section key={group} className="mt-6">
          <h2 className="text-lg font-serif font-semibold">{groupLabel[group] ?? group}</h2>
          <ul className="mt-3 space-y-2">
            {items.map((s) => (
              <li
                key={s.slug}
                className="flex items-center justify-between rounded-md border border-stone-200 px-4 py-3 dark:border-stone-800"
              >
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="font-mono text-xs text-stone-500">{s.slug}</p>
                </div>
                <SourceToggle slug={s.slug} enabled={s.enabled} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd web && pnpm build
```

- [ ] **Step 5: Commit**

```bash
git add web/app/fuentes/ web/components/SourceToggle.tsx web/app/api/sources/
git commit -m "feat(web): fuentes page with enable/disable toggle"
```

---

## Phase 7: Refresh button + polling

### Task 26: Web proxy routes for refresh and runs

**Files:**
- Create: `web/app/api/refresh/route.ts`
- Create: `web/app/api/runs/[id]/route.ts`
- Create: `web/app/api/runs/current/route.ts`

- [ ] **Step 1: Write `web/app/api/refresh/route.ts`**

```ts
import { NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function POST() {
  const res = await fetch(`${INTERNAL}/refresh`, { method: "POST" });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

- [ ] **Step 2: Write `web/app/api/runs/[id]/route.ts`**

```ts
import { NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const res = await fetch(`${INTERNAL}/runs/${id}`, { cache: "no-store" });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

- [ ] **Step 3: Write `web/app/api/runs/current/route.ts`**

```ts
import { NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET() {
  const res = await fetch(`${INTERNAL}/runs/current`, { cache: "no-store" });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add web/app/api/refresh/ web/app/api/runs/
git commit -m "feat(web): proxy routes for refresh and runs polling"
```

---

### Task 27: RefreshButton component with polling

**Files:**
- Create: `web/components/RefreshButton.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Write `web/components/RefreshButton.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { RunDetail } from "@/lib/types";

type State =
  | { kind: "idle" }
  | { kind: "running"; runId: number | null; phase: string }
  | { kind: "error"; message: string };

const TERMINAL = new Set<RunDetail["status"]>(["success", "partial", "failed"]);

export function RefreshButton() {
  const [state, setState] = useState<State>({ kind: "idle" });
  const pollRef = useRef<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  function startPolling(runId: number | null) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      const url = runId ? `/api/runs/${runId}` : "/api/runs/current";
      const res = await fetch(url);
      if (!res.ok) return;
      const run = (await res.json()) as RunDetail | null;
      if (!run) return;
      const phase = describePhase(run);
      setState({ kind: "running", runId: run.id, phase });
      if (TERMINAL.has(run.status)) {
        if (pollRef.current) window.clearInterval(pollRef.current);
        if (run.status === "failed") {
          setState({ kind: "error", message: run.error ?? "Falló el pipeline" });
        } else {
          setState({ kind: "idle" });
          router.refresh();
        }
      }
    }, 2000);
  }

  async function trigger() {
    setState({ kind: "running", runId: null, phase: "Encolando..." });
    const res = await fetch("/api/refresh", { method: "POST" });
    if (res.status === 202 || res.status === 409) {
      const body = await res.json().catch(() => null);
      const runId = body?.run_id ?? body?.detail?.run_id ?? null;
      startPolling(runId);
      return;
    }
    setState({ kind: "error", message: `Error ${res.status}` });
  }

  return (
    <div className="flex items-center gap-3">
      {state.kind === "error" && (
        <span className="text-sm text-red-600 dark:text-red-400">{state.message}</span>
      )}
      {state.kind === "running" && (
        <span className="text-sm text-stone-600 dark:text-stone-400">{state.phase}</span>
      )}
      <button
        type="button"
        onClick={trigger}
        disabled={state.kind === "running"}
        className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
      >
        {state.kind === "running" ? "Procesando..." : "Actualizar"}
      </button>
    </div>
  );
}

function describePhase(run: RunDetail): string {
  if (run.status === "queued") return "En cola...";
  if (run.status === "running") {
    const stats = run.stats as Record<string, number> | null;
    if (stats?.analyzed && stats.analyzed > 0) return `Analizando (${stats.analyzed})...`;
    if (stats?.embedded && stats.embedded > 0) return `Generando embeddings...`;
    if (stats?.persisted && stats.persisted > 0) return `Recolectando notas...`;
    return "Procesando...";
  }
  return run.status;
}
```

- [ ] **Step 2: Re-enable RefreshButton in `web/app/page.tsx`**

Restore (or add back) the import and usage. Replace placeholder with actual import:

```tsx
import { RefreshButton } from "@/components/RefreshButton";
```

And replace the placeholder comment with `<RefreshButton />` in the header div.

- [ ] **Step 3: Verify build**

```bash
cd web && pnpm build
```

- [ ] **Step 4: Commit**

```bash
git add web/components/RefreshButton.tsx web/app/page.tsx
git commit -m "feat(web): RefreshButton with polling and phase display"
```

---

## Phase 8: Polish

### Task 28: Backup script

**Files:**
- Create: `scripts/backup.sh`
- Modify: `README.md`

- [ ] **Step 1: Write `scripts/backup.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/noticias-${STAMP}.dump"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-noticias}" -F c "${POSTGRES_DB:-noticias}" > "$OUT"
echo "Backup saved: $OUT"

# Rotate
find "$BACKUP_DIR" -name "noticias-*.dump" -type f -mtime "+${RETAIN_DAYS}" -delete
echo "Rotated backups older than ${RETAIN_DAYS} days."
```

- [ ] **Step 2: Make executable and test**

```bash
chmod +x scripts/backup.sh
docker compose up postgres -d
./scripts/backup.sh
ls backups/
```

Expected: a `noticias-<timestamp>.dump` file.

- [ ] **Step 3: Document in README under "Backups" section**

Append to `README.md`:

```markdown
## Backups

```bash
./scripts/backup.sh
```

Para correr automáticamente, agregar a crontab del host:

```
0 4 * * * cd /path/to/noticias && ./scripts/backup.sh >> /var/log/noticias-backup.log 2>&1
```

Restaurar:

```bash
docker compose exec -T postgres pg_restore -U noticias -d noticias < backups/noticias-XXXX.dump
```
```

- [ ] **Step 4: Commit**

```bash
git add scripts/ README.md
git commit -m "feat: backup script with rotation + docs"
```

---

### Task 29: README finalization and end-to-end smoke

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Expand `README.md` with full quickstart**

Replace `README.md` content with:

```markdown
# Noticias

Compara cómo distintos diarios argentinos cubren las mismas noticias.
Pipeline Python (FastAPI) + frontend Next.js + Postgres con pgvector.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, APScheduler
- **Frontend:** Next.js 15, React 19, Tailwind 4, next-themes
- **DB:** Postgres 16 + pgvector
- **LLM:** OpenAI (embeddings + GPT-4o)

## Diarios cubiertos

- Mainstream: La Nación, Clarín, Infobae
- Crítico: Página 12, Tiempo Argentino, El Destape
- Económico: Ámbito, El Cronista, BAE Negocios

## Quickstart

1. Copiar y editar variables:

   ```bash
   cp .env.example .env
   # editar OPENAI_API_KEY
   ```

2. Levantar todo:

   ```bash
   docker compose up --build
   ```

3. Aplicar migraciones (la primera vez):

   ```bash
   docker compose exec api alembic upgrade head
   ```

4. Sembrar fuentes (la primera vez):

   ```bash
   docker compose exec api python -c "
   import asyncio
   from noticias_api.db.session import async_session_factory
   from noticias_api.db.seed import seed_sources
   async def main():
       async with async_session_factory() as s:
           print(await seed_sources(s))
   asyncio.run(main())
   "
   ```

5. Visitar http://localhost:3000 — tocar **Actualizar** para correr el pipeline manualmente.

## Estructura

- `api/` — backend Python
- `web/` — frontend Next.js
- `scripts/` — backups y utilidades
- `docs/superpowers/` — specs y planes

## Configuración relevante (.env)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | API key de OpenAI (requerido) |
| `CRON_HOUR` | 7 | Hora del cron diario |
| `TOP_N_CLUSTERS` | 15 | Cuántas historias destacar por día |
| `SIMILARITY_THRESHOLD` | 0.78 | Umbral coseno para clustering |

## Backups

```bash
./scripts/backup.sh
```

## Tests

API:

```bash
cd api && pytest -v
```

Frontend (build smoke):

```bash
cd web && pnpm build
```
```

- [ ] **Step 2: Run end-to-end smoke**

```bash
docker compose up --build -d
sleep 10
docker compose exec api alembic upgrade head
docker compose exec api python -c "
import asyncio
from noticias_api.db.session import async_session_factory
from noticias_api.db.seed import seed_sources
async def main():
    async with async_session_factory() as s:
        print(await seed_sources(s))
asyncio.run(main())
"
curl -s http://localhost:8000/healthz | grep ok
curl -s http://localhost:8000/sources | head -c 200
echo
curl -s http://localhost:3000 -o /dev/null -w "%{http_code}\n"
```

Expected: `{"status":"ok"}`, JSON of 9 sources, `200` from web.

- [ ] **Step 3: Tear down**

```bash
docker compose down
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: full README with quickstart, config, backup, test instructions"
```

---

## Self-Review Notes

This plan covers every section of the spec. Mapping:

| Spec section | Tasks |
|--------------|-------|
| §3 Architecture | Tasks 2, 3, 19 |
| §4 Data model | Tasks 5, 6 |
| §5 Pipeline | Tasks 8-15 |
| §6 API REST | Tasks 7, 16, 17, 18 |
| §7 Frontend | Tasks 19-25, 27 |
| §8 Errors/observability | Tasks 15, 16 (errors_per_source in stats; healthz exists; /runs visible) |
| §9 Testing | Tests interleaved in every TDD task |
| §10 Repo structure | Task 1 |
| §11 Deployment | Tasks 2, 3, 19, 28, 29 |

Out-of-scope items (spec §12) are explicitly not implemented.

**Type consistency:** Pipeline step signatures consumed by `runner.py` (Task 15) match the implementations in Tasks 8-14: `fetch_feed`, `parse_feed`, `persist_items`, `extract_content`, `embed_texts` (with `build_embedding_input`), `cluster_recent_articles`, `rank_top_clusters`, `analyze_cluster`. The `AnalysisResult` Pydantic model from Task 14 is what the runner persists into `Analysis` rows.

**Frontend type contracts:** `web/lib/types.ts` (Task 20) mirrors the FastAPI Pydantic response models defined in Tasks 17 and 18 (`BriefingOut`, `ClusterDetail`, `AnalysisOut`, etc.). Property names match exactly.

**No placeholders:** All steps include actual code or commands. The only deferred wiring is `RefreshButton` in Task 22 (placeholder until Task 27), which is noted explicitly.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-08-noticias-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?



