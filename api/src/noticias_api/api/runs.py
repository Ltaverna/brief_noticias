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
    asyncio.create_task(_run_locked("manual", settings))
    # The run_id will only exist after _run_locked creates the Run row.
    # We immediately return queued; the client polls /runs/current to get the actual id.
    return RefreshResponse(run_id=0, status="queued")


@router.get("/runs/current", response_model=RunOut | None)
async def current_run(session: AsyncSession = Depends(get_session)) -> Run | None:
    run_id = get_current_run_id()
    if run_id is None:
        return None
    return await session.get(Run, run_id)


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
