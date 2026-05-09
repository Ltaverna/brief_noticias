import hashlib
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings
from noticias_api.db.models import Analysis, Article, Cluster, Delivery, Source
from noticias_api.notifiers.telegram import (
    TelegramClient,
    TelegramError,
    escape_markdown_v2 as esc,
)

logger = logging.getLogger(__name__)

CHANNEL_TELEGRAM = "telegram"
MAX_LENGTH = 4000  # Telegram limit is 4096; leave headroom


async def build_digest(
    session: AsyncSession, target: date, public_base_url: str
) -> str:
    """Build a MarkdownV2-formatted digest message for the given date."""
    clusters = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.display_date == target)
            .order_by(Cluster.rank_score.desc().nullslast())
        )
    ).all()

    header = f"📰 *Briefing {esc(str(target))}*"

    if not clusters:
        return f"{header}\n\n_No hay briefing para esta fecha todavía{esc('.')}_"

    parts: list[str] = [header, ""]
    total_len = sum(len(p) + 1 for p in parts)
    truncated = 0

    for c in clusters:
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == c.id)
        )
        title = (
            analysis.headline
            if analysis and analysis.headline
            else "(análisis pendiente)"
        )
        slugs_result = await session.scalars(
            select(Source.slug)
            .join(Article, Article.source_id == Source.id)
            .where(Article.cluster_id == c.id)
            .distinct()
        )
        slugs = sorted(slugs_result.all())
        link = f"{public_base_url}/cluster/{c.id}"

        block = (
            f"🎯 *{esc(title)}*\n"
            f"_{c.source_count} diarios · {esc(', '.join(slugs))}_\n"
            f"[Ver detalle]({esc(link)})\n"
        )

        if total_len + len(block) > MAX_LENGTH - 80:
            truncated = len(clusters) - clusters.index(c)
            break
        parts.append(block)
        total_len += len(block) + 1

    if truncated:
        parts.append(f"_y {truncated} historias más{esc('...')}_")

    return "\n".join(parts)


def hash_message(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def send_digest(
    session: AsyncSession,
    settings: Settings,
    target: date,
    *,
    force: bool = False,
) -> int | None:
    """Send digest via Telegram. Returns message_id, or None if skipped (already sent or disabled).

    Idempotent: same (channel, chat_id, date, message_hash) is not re-sent unless force=True.
    """
    if (
        not settings.enable_telegram
        or not settings.telegram_bot_token
        or not settings.telegram_chat_id
    ):
        logger.info("digest skipped: telegram not configured")
        return None

    text = await build_digest(session, target, settings.public_base_url)
    msg_hash = hash_message(text)

    if not force:
        existing = await session.scalar(
            select(Delivery).where(
                Delivery.channel == CHANNEL_TELEGRAM,
                Delivery.chat_id == settings.telegram_chat_id,
                Delivery.display_date == target,
                Delivery.message_hash == msg_hash,
                Delivery.status == "sent",
            )
        )
        if existing:
            logger.info("digest already sent for %s (hash %s)", target, msg_hash[:8])
            return None

    client = TelegramClient(settings.telegram_bot_token)

    # Upsert a pending delivery row (handles force resend gracefully via ON CONFLICT DO UPDATE).
    stmt = (
        pg_insert(Delivery)
        .values(
            channel=CHANNEL_TELEGRAM,
            chat_id=settings.telegram_chat_id,
            display_date=target,
            message_hash=msg_hash,
            status="pending",
            error=None,
        )
        .on_conflict_do_update(
            constraint="uq_deliveries_chan_chat_date_hash",
            set_={"status": "pending", "error": None},
        )
        .returning(Delivery)
    )
    result = await session.execute(stmt)
    delivery = result.scalar_one()
    await session.flush()

    try:
        msg_id = await client.send_message(settings.telegram_chat_id, text)
    except TelegramError as exc:
        delivery.status = "failed"
        delivery.error = str(exc)[:500]
        await session.commit()
        logger.exception("telegram send failed")
        raise

    delivery.status = "sent"
    await session.commit()
    return msg_id
