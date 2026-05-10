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
    # Patch _extract_for_articles which runs OUTSIDE the per-source try/except,
    # so its RuntimeError bubbles up to the outer exception handler.
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._extract_for_articles",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    # Also patch _fetch_source_items so the per-source loop succeeds (no sources anyway)
    monkeypatch.setattr(
        "noticias_api.pipeline.runner._fetch_source_items",
        AsyncMock(return_value=[]),
    )

    with pytest.raises(RuntimeError):
        await run_pipeline(db_session, pipeline_config, trigger="cron")

    run = (await db_session.scalars(select(Run).order_by(Run.id.desc()))).first()
    assert run.status == "failed"
    assert "boom" in run.error
