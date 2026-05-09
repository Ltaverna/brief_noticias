import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from noticias_api.api import analytics, briefings, clusters, entities, qa, runs, sagas, search, sources, subscriptions
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
app.include_router(analytics.router)
app.include_router(sources.router)
app.include_router(runs.router)
app.include_router(briefings.router)
app.include_router(clusters.router)
app.include_router(sagas.router)
app.include_router(search.router)
app.include_router(entities.router)
app.include_router(qa.router)
app.include_router(subscriptions.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
