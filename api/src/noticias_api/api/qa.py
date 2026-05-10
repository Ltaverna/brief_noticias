import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.session import get_session
from noticias_api.qa.crag import EMPTY_ANSWER, evaluate_relevance, filter_chunks
from noticias_api.qa.hyde import generate_hypothetical
from noticias_api.qa.memory import append_messages, load_recent_history, new_conversation_id
from noticias_api.qa.retrieval import retrieve_chunks
from noticias_api.qa.synthesis import synthesize

logger = logging.getLogger(__name__)

router = APIRouter(tags=["qa"])


class QARequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    conversation_id: str | None = Field(default=None, max_length=64)


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
    conversation_id: str
    hyde_query: str | None = None
    confidence: str = "confident"  # 'confident' | 'partial' | 'empty'
    crag_verdicts: dict[str, str] | None = None


@router.post("/qa", response_model=QAResponse)
async def ask_qa(
    body: QARequest,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> QAResponse:
    if not settings.openai_api_key:
        raise HTTPException(500, "openai not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    conversation_id = body.conversation_id or new_conversation_id()

    # 1. HyDE — generate a hypothetical answer to embed for retrieval
    hypothetical: str | None = None
    if settings.enable_hyde:
        try:
            hypothetical = await generate_hypothetical(
                client, query=body.query, model=settings.hyde_model
            )
        except Exception:
            logger.exception("hyde failed; falling back to raw query")

    # 2. Retrieve (kNN + optional Cohere rerank)
    chunks = await retrieve_chunks(
        session,
        client,
        query=body.query,
        embedding_model=settings.embedding_model,
        hypothetical=hypothetical,
        settings=settings,
    )
    if not chunks:
        return QAResponse(
            query=body.query,
            answer="No hay material indexado todavía. Corré el pipeline al menos una vez.",
            used_citations=[],
            citations=[],
            conversation_id=conversation_id,
            hyde_query=hypothetical,
        )

    # 3. CRAG-lite — evaluate chunk relevance and decide strategy
    crag_confidence: str = "confident"
    crag_verdicts: dict[str, str] | None = None
    filtered_chunks = chunks

    if settings.enable_crag:
        crag = await evaluate_relevance(
            client,
            query=body.query,
            chunks=chunks,
            model=settings.crag_model,
            min_relevant=settings.crag_min_relevant,
        )
        crag_confidence = crag.confidence
        crag_verdicts = {str(k): v for k, v in crag.verdicts.items()}
        filtered_chunks = filter_chunks(chunks, crag)

        if crag.confidence == "empty":
            # Short-circuit: return honest "no encontré"
            await append_messages(
                session,
                conversation_id,
                body.query,
                EMPTY_ANSWER,
                citations=[],
                used_citations=[],
                hyde_query=hypothetical,
                model="crag-empty",
            )
            return QAResponse(
                query=body.query,
                answer=EMPTY_ANSWER,
                used_citations=[],
                citations=[],
                conversation_id=conversation_id,
                hyde_query=hypothetical,
                confidence="empty",
                crag_verdicts=crag_verdicts,
            )

    # 4. Load conversation history
    history_msgs = await load_recent_history(
        session, conversation_id, max_turns=settings.qa_history_turns
    )
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # 5. Synthesize answer (uses filtered chunks; [N] markers renumbered 1..len)
    result = await synthesize(
        client,
        question=body.query,
        chunks=filtered_chunks,
        model=settings.chat_model_analysis,
        history=history,
        confidence_hint=crag_confidence,
    )

    # 6. Build citations payload (renumbered to match filtered_chunks)
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
        for i, c in enumerate(filtered_chunks)
    ]

    # 7. Persist both turns
    await append_messages(
        session,
        conversation_id,
        body.query,
        result.answer,
        citations=[c.model_dump(mode="json") for c in citations],
        used_citations=result.used_citations,
        hyde_query=hypothetical,
        model=settings.chat_model_analysis,
    )

    return QAResponse(
        query=body.query,
        answer=result.answer,
        used_citations=result.used_citations,
        citations=citations,
        conversation_id=conversation_id,
        hyde_query=hypothetical,
        confidence=crag_confidence,
        crag_verdicts=crag_verdicts,
    )


@router.get("/qa/history", response_model=list[dict])
async def qa_history(
    conversation_id: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return recent messages for a conversation (oldest first)."""
    msgs = await load_recent_history(session, conversation_id, max_turns=limit)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations,
            "used_citations": m.used_citations,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]
