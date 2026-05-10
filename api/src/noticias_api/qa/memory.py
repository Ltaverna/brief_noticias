import logging
import secrets
from typing import Final

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import QaMessage

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS: Final = 12  # safety cap regardless of config


def new_conversation_id() -> str:
    """Generate a cryptographically random, URL-safe conversation identifier."""
    return secrets.token_urlsafe(16)


async def load_recent_history(
    session: AsyncSession,
    conversation_id: str,
    *,
    max_turns: int = 6,
) -> list[QaMessage]:
    """Return the last `max_turns` user/assistant pairs (up to 2*max_turns rows)
    for the given conversation, in chronological order (oldest first).
    """
    if not conversation_id:
        return []
    capped = min(max_turns, MAX_HISTORY_TURNS)
    rows = (
        await session.scalars(
            select(QaMessage)
            .where(QaMessage.conversation_id == conversation_id)
            .order_by(desc(QaMessage.created_at), desc(QaMessage.id))
            .limit(capped * 2)
        )
    ).all()
    return list(reversed(rows))


async def append_messages(
    session: AsyncSession,
    conversation_id: str,
    user_query: str,
    assistant_answer: str,
    *,
    citations: list[dict] | None = None,
    used_citations: list[int] | None = None,
    hyde_query: str | None = None,
    model: str | None = None,
) -> None:
    """Persist the user question and assistant answer as a pair of QaMessage rows."""
    session.add_all([
        QaMessage(
            conversation_id=conversation_id,
            role="user",
            content=user_query,
        ),
        QaMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_answer,
            citations=citations,
            used_citations=used_citations,
            hyde_query=hyde_query,
            model=model,
        ),
    ])
    await session.commit()
