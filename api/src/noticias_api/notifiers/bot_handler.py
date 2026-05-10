import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings
from noticias_api.notifiers.telegram import (
    TelegramClient,
    TelegramError,
    escape_markdown_v2 as esc,
)
from noticias_api.qa.crag import EMPTY_ANSWER, evaluate_relevance, filter_chunks
from noticias_api.qa.hyde import generate_hypothetical
from noticias_api.qa.memory import append_messages, load_recent_history
from noticias_api.qa.retrieval import RetrievedChunk, retrieve_chunks
from noticias_api.qa.synthesis import synthesize

logger = logging.getLogger(__name__)


WELCOME = (
    "👋 Hola\\. Soy el bot de *Noticias*\\.\n\n"
    "Hacé una pregunta sobre el corpus de diarios argentinos y te respondo con citas\\.\n"
    "Comandos: /help"
)

HELP = (
    "*Comandos disponibles*:\n\n"
    "• Cualquier texto → pregunta libre al corpus\n"
    "• /start → mensaje de bienvenida\n"
    "• /help → este mensaje\n\n"
    "_Ejemplo: ¿qué dijo La Nación esta semana sobre Adorni?_"
)


def allowed_chats(settings: Settings) -> set[str]:
    """Return the set of chat_ids allowed to interact with the bot."""
    raw = settings.telegram_allowed_chats
    if raw:
        return {c.strip() for c in raw.split(",") if c.strip()}
    if settings.telegram_chat_id:
        return {settings.telegram_chat_id}
    return set()


async def handle_update(
    update: dict[str, Any],
    *,
    settings: Settings,
    session: AsyncSession,
) -> None:
    """Process a single Telegram Update payload. Idempotent on bad payloads."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id_raw = chat.get("id")
    if chat_id_raw is None:
        return
    chat_id = str(chat_id_raw)

    allowed = allowed_chats(settings)
    if allowed and chat_id not in allowed:
        logger.warning("ignoring message from unauthorized chat %s", chat_id)
        return

    text = (msg.get("text") or "").strip()
    if not text:
        return

    if not settings.telegram_bot_token:
        logger.error("bot enabled but no token")
        return
    bot = TelegramClient(settings.telegram_bot_token)

    if text.startswith("/start"):
        await bot.send_message(chat_id, WELCOME)
        return
    if text.startswith("/help"):
        await bot.send_message(chat_id, HELP)
        return
    if text.startswith("/"):
        await bot.send_message(
            chat_id, esc("Comando no reconocido. Probá /help.")
        )
        return

    # Treat as Q&A — send placeholder immediately for good UX
    placeholder_msg_id = await bot.send_message(
        chat_id, "🤔 Pensando\\.\\.\\."
    )

    # Use a stable conversation_id per Telegram chat so memory persists across
    # multiple messages in the same chat.
    conv_id = f"telegram:{chat_id}"

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # 1. HyDE
        hypothetical: str | None = None
        if settings.enable_hyde:
            try:
                hypothetical = await generate_hypothetical(
                    client, query=text, model=settings.hyde_model
                )
            except Exception:
                logger.exception("hyde failed; falling back to raw query")

        # 2. Retrieve (kNN + optional rerank)
        chunks = await retrieve_chunks(
            session,
            client,
            query=text,
            embedding_model=settings.embedding_model,
            hypothetical=hypothetical,
            settings=settings,
        )
        if not chunks:
            await bot.edit_message_text(
                chat_id,
                placeholder_msg_id,
                esc("No hay material indexado todavía."),
            )
            return

        # 3. CRAG-lite — evaluate chunk relevance and decide strategy
        crag_confidence: str = "confident"
        filtered_chunks = chunks

        if settings.enable_crag:
            crag = await evaluate_relevance(
                client,
                query=text,
                chunks=chunks,
                model=settings.crag_model,
                min_relevant=settings.crag_min_relevant,
            )
            crag_confidence = crag.confidence
            filtered_chunks = filter_chunks(chunks, crag)

            if crag.confidence == "empty":
                await bot.edit_message_text(
                    chat_id, placeholder_msg_id, esc(EMPTY_ANSWER)
                )
                await append_messages(
                    session,
                    conv_id,
                    text,
                    EMPTY_ANSWER,
                    citations=[],
                    used_citations=[],
                    hyde_query=hypothetical,
                    model="crag-empty",
                )
                return

        # 4. Load history
        history_msgs = await load_recent_history(
            session, conv_id, max_turns=settings.qa_history_turns
        )
        history = [{"role": m.role, "content": m.content} for m in history_msgs]

        # 5. Synthesize
        result = await synthesize(
            client,
            question=text,
            chunks=filtered_chunks,
            model=settings.chat_model_analysis,
            history=history,
            confidence_hint=crag_confidence,
        )

        # 6. Send response (formatted against filtered_chunks for correct [N] mapping)
        formatted = format_qa_response(text, result.answer, result.used_citations, filtered_chunks)
        await bot.edit_message_text(chat_id, placeholder_msg_id, formatted)

        # 7. Persist
        await append_messages(
            session,
            conv_id,
            text,
            result.answer,
            used_citations=result.used_citations,
            hyde_query=hypothetical,
            model=settings.chat_model_analysis,
        )

    except Exception as exc:
        logger.exception("qa handler failed")
        try:
            await bot.edit_message_text(
                chat_id,
                placeholder_msg_id,
                f"❌ Error procesando la pregunta: {esc(str(exc)[:200])}",
            )
        except TelegramError:
            pass


def format_qa_response(
    question: str,
    answer: str,
    used_citations: list[int],
    chunks: list[RetrievedChunk],
) -> str:
    """Build a MarkdownV2 message: the answer body with citations as a tail block."""
    lines: list[str] = []
    # Escape the answer text; [N] citation markers are preserved as-is because
    # digits and square brackets are escaped individually and the pattern
    # \\[N\\] is still readable. We intentionally escape so raw answer is safe.
    lines.append(esc(answer))

    # Only render citations that are within bounds
    valid_citations = [n for n in used_citations if 1 <= n <= len(chunks)]
    if valid_citations:
        lines.append("")
        lines.append("*Fuentes*")
        for n in valid_citations:
            c = chunks[n - 1]
            date_str = (
                c.published_at.strftime("%Y-%m-%d") if c.published_at else "s/f"
            )
            link_label = esc(c.source_slug + " \\- " + date_str)
            safe_url = c.url.replace(")", "\\)")
            lines.append(f"\\[{n}\\] [{link_label}]({safe_url})")

    msg = "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:3990] + esc("...")
    return msg
