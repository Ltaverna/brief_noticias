import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings
from noticias_api.db.models import (
    AlertDelivery,
    Analysis,
    Article,
    Cluster,
    ClusterEntity,
    Entity,
    Source,
    Subscription,
)
from noticias_api.notifiers.telegram import (
    TelegramClient,
    TelegramError,
    escape_markdown_v2 as esc,
)

logger = logging.getLogger(__name__)
CHANNEL_TELEGRAM = "telegram"


async def detect_and_send_alerts(
    session: AsyncSession,
    settings: Settings,
) -> dict[str, int]:
    """Detect new clusters that match a subscription with alert_threshold_sources set,
    and that haven't already triggered an alert for that subscription+cluster pair.

    Idempotency: alert_deliveries has a unique constraint on
    (channel, chat_id, cluster_id, subscription_id).
    """
    if not settings.enable_telegram or not settings.telegram_bot_token:
        return {"alerts_sent": 0}

    # Load subscriptions with alert thresholds
    subs = (
        await session.scalars(
            select(Subscription)
            .where(Subscription.channel == CHANNEL_TELEGRAM)
            .where(Subscription.alert_threshold_sources.is_not(None))
        )
    ).all()

    if not subs:
        return {"alerts_sent": 0}

    client = TelegramClient(settings.telegram_bot_token)
    sent = 0

    for sub in subs:
        # Build candidate cluster query based on subscription kind
        if sub.kind == "entity" and sub.value:
            canon = sub.value.lower().strip()
            stmt = (
                select(Cluster)
                .join(ClusterEntity, ClusterEntity.cluster_id == Cluster.id)
                .join(Entity, Entity.id == ClusterEntity.entity_id)
                .where(Entity.canonical == canon)
                .where(Cluster.source_count >= sub.alert_threshold_sources)
            )
        elif sub.kind == "all":
            stmt = select(Cluster).where(
                Cluster.source_count >= sub.alert_threshold_sources
            )
        else:
            # topic alerts not yet implemented
            continue

        candidates = (await session.scalars(stmt)).all()

        for cluster in candidates:
            # Idempotency: already sent for this (sub, cluster)?
            existing = await session.scalar(
                select(AlertDelivery)
                .where(AlertDelivery.channel == CHANNEL_TELEGRAM)
                .where(AlertDelivery.chat_id == sub.chat_id)
                .where(AlertDelivery.cluster_id == cluster.id)
                .where(AlertDelivery.subscription_id == sub.id)
            )
            if existing:
                continue

            analysis = await session.scalar(
                select(Analysis).where(Analysis.cluster_id == cluster.id)
            )

            slugs = (
                await session.scalars(
                    select(Source.slug)
                    .join(Article, Article.source_id == Source.id)
                    .where(Article.cluster_id == cluster.id)
                    .distinct()
                )
            ).all()

            headline = (
                analysis.headline
                if analysis and analysis.headline
                else f"(cluster {cluster.id})"
            )
            link = f"{settings.public_base_url}/cluster/{cluster.id}"
            sub_label = (
                f"watch · {sub.value}"
                if sub.kind == "entity" and sub.value
                else "umbral global"
            )

            text = (
                f"🚨 *Alerta {esc(sub_label)}*\n"
                f"*{esc(headline)}*\n"
                f"_{cluster.source_count} diarios · {esc(', '.join(sorted(slugs)))}_\n"
                f"[Ver detalle]({esc(link)})"
            )

            delivery = AlertDelivery(
                channel=CHANNEL_TELEGRAM,
                chat_id=sub.chat_id,
                cluster_id=cluster.id,
                subscription_id=sub.id,
                status="pending",
            )
            session.add(delivery)
            await session.flush()

            try:
                await client.send_message(sub.chat_id, text)
                delivery.status = "sent"
            except TelegramError as exc:
                delivery.status = "failed"
                delivery.error = str(exc)[:500]
                logger.warning(
                    "alert send failed for sub=%s cluster=%s: %s",
                    sub.id, cluster.id, exc,
                )
            await session.commit()

            if delivery.status == "sent":
                sent += 1

    return {"alerts_sent": sent}
