from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.session import get_session
from noticias_api.qa.retrieval import retrieve_chunks
from noticias_api.qa.synthesis import synthesize

router = APIRouter(tags=["qa"])


class QARequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class QACitation(BaseModel):
    n: int
    article_id: int
    cluster_id: int | None
    source_slug: str
    source_name: str
    title: str
    url: str
    published_at: datetime | None
    snippet: str


class QAResponse(BaseModel):
    query: str
    answer: str
    used_citations: list[int]
    citations: list[QACitation]


@router.post("/qa", response_model=QAResponse)
async def ask_qa(
    body: QARequest,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> QAResponse:
    if not settings.openai_api_key:
        raise HTTPException(500, "openai not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    chunks = await retrieve_chunks(
        session, client, query=body.query,
        embedding_model=settings.embedding_model,
    )
    if not chunks:
        return QAResponse(
            query=body.query,
            answer="No hay material indexado todavía. Corré el pipeline al menos una vez.",
            used_citations=[],
            citations=[],
        )
    result = await synthesize(
        client, question=body.query, chunks=chunks,
        model=settings.chat_model_analysis,
    )

    citations = [
        QACitation(
            n=i + 1,
            article_id=c.article_id,
            cluster_id=c.cluster_id,
            source_slug=c.source_slug,
            source_name=c.source_name,
            title=c.title,
            url=c.url,
            published_at=c.published_at,
            snippet=c.snippet,
        )
        for i, c in enumerate(chunks)
    ]
    return QAResponse(
        query=body.query,
        answer=result.answer,
        used_citations=result.used_citations,
        citations=citations,
    )
