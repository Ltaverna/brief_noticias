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
