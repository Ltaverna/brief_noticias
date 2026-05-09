import logging
import math
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Cluster

logger = logging.getLogger(__name__)

MIN_SOURCE_COUNT = 2


async def rank_top_clusters(session: AsyncSession, *, top_n: int) -> None:
    """Compute rank_score for clusters and mark top N as is_top with display_date=today."""
    today = date.today()
    now = datetime.now(UTC)

    candidates = (
        await session.scalars(
            select(Cluster)
            .where(Cluster.source_count >= MIN_SOURCE_COUNT)
            .where(Cluster.last_seen_at.is_not(None))
        )
    ).all()

    scored: list[tuple[Cluster, float]] = []
    for c in candidates:
        last_seen = c.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        hours_ago = max(0.0, (now - last_seen).total_seconds() / 3600.0)
        score = c.source_count * 2 + math.log(c.article_count + 1) - hours_ago * 0.05
        scored.append((c, score))

    scored.sort(key=lambda t: t[1], reverse=True)

    # reset all is_top first
    await session.execute(update(Cluster).values(is_top=False))

    for cluster, score in scored[:top_n]:
        cluster.rank_score = score
        cluster.is_top = True
        cluster.display_date = today

    await session.commit()
