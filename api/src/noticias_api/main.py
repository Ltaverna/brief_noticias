from fastapi import FastAPI

from noticias_api.api import sources

app = FastAPI(title="Noticias API", version="0.1.0")
app.include_router(sources.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
