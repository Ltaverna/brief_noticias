import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from noticias_api.api import (
    analytics,
    briefings,
    clusters,
    entities,
    notes,
    qa,
    runs,
    sagas,
    search,
    sources,
    subscriptions,
    telegram_admin,
    telegram_webhook,
)
from noticias_api.config import get_settings
from noticias_api.scheduler import setup_scheduler, teardown_polling

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
        teardown_polling()


app = FastAPI(title="Noticias API", version="0.1.0", lifespan=lifespan)
app.include_router(analytics.router)
app.include_router(sources.router)
app.include_router(runs.router)
app.include_router(briefings.router)
app.include_router(clusters.router)
app.include_router(notes.router)
app.include_router(sagas.router)
app.include_router(search.router)
app.include_router(entities.router)
app.include_router(qa.router)
app.include_router(subscriptions.router)
app.include_router(telegram_admin.router)
app.include_router(telegram_webhook.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
