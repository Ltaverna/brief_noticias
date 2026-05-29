"""Centroid + profile_vector por autor.

Centroid: AVG(article.embedding) sobre artículos del autor.
Profile vector (20 dims): 10 topic dist + 1 tone + 1 omission + 1 divergence +
                          1 framing_diversity + 6 monthly activity buckets.

Skip si article_count no cambió desde centroid_updated_at (heurística simple).
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import (
    Article,
    ArticleAuthor,
    Author,
    Cluster,
)

PROFILE_DIM = 20
TOPIC_SLOTS = 10  # primeros 10 topics conocidos (orden alfabético)


async def _known_topics(session: AsyncSession) -> list[str]:
    rows = (
        await session.execute(
            select(Cluster.topic, func.count(Cluster.id))
            .where(Cluster.topic.isnot(None))
            .group_by(Cluster.topic)
            .order_by(Cluster.topic)
            .limit(TOPIC_SLOTS)
        )
    ).all()
    return [r[0] for r in rows]


async def _compute_centroid(session: AsyncSession, author_id: int) -> list[float] | None:
    embeddings = (
        await session.scalars(
            select(Article.embedding)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(
                ArticleAuthor.author_id == author_id,
                Article.embedding.isnot(None),
            )
        )
    ).all()
    if not embeddings:
        return None
    n = len(embeddings)
    dim = len(embeddings[0])
    sums = [0.0] * dim
    for emb in embeddings:
        for i, v in enumerate(emb):
            sums[i] += float(v)
    return [s / n for s in sums]


async def _compute_profile_vector(
    session: AsyncSession, author_id: int, topics: list[str]
) -> list[float] | None:
    # Topic distribution
    topic_counts: dict[str, int] = {}
    total_articles = 0
    rows = (
        await session.execute(
            select(Cluster.topic, func.count(Article.id))
            .join(Article, Article.cluster_id == Cluster.id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author_id)
            .group_by(Cluster.topic)
        )
    ).all()
    for topic, cnt in rows:
        total_articles += int(cnt)
        if topic in topics:
            topic_counts[topic] = int(cnt)

    topic_vec = [0.0] * TOPIC_SLOTS
    if total_articles:
        for i, t in enumerate(topics):
            topic_vec[i] = topic_counts.get(t, 0) / total_articles

    if total_articles == 0:
        return None

    from noticias_api.api._aggregations import stats_by_author
    stats = await stats_by_author(session, author_id)
    tone = stats.get("tone_avg") or 0.0
    omission = stats.get("omission_rate") or 0.0
    divergence = stats.get("divergence_score") or 0.0
    framing_diversity = stats.get("framing_diversity") or 0.0
    # Clamp a [-1, 1]
    tone = max(-1.0, min(1.0, tone))
    omission = max(-1.0, min(1.0, omission))
    divergence = max(-1.0, min(1.0, divergence))
    framing_diversity = max(-1.0, min(1.0, framing_diversity))

    # Activity: últimos 6 meses, cuenta normalizada
    now = datetime.now(UTC)
    monthly = [0.0] * 6
    for i in range(6):
        month_end = now - timedelta(days=30 * i)
        month_start = month_end - timedelta(days=30)
        cnt = await session.scalar(
            select(func.count(Article.id))
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(
                ArticleAuthor.author_id == author_id,
                Article.published_at >= month_start,
                Article.published_at < month_end,
            )
        )
        monthly[i] = float(cnt or 0)
    max_monthly = max(monthly) or 1.0
    monthly = [m / max_monthly for m in monthly]

    return topic_vec + [tone, omission, divergence, framing_diversity] + monthly


async def update_author_vectors(session: AsyncSession) -> dict:
    """Recompute centroid + profile_vector for authors with new articles.

    Heurística simple: si el autor tiene artículos pero centroid es NULL
    o centroid_updated_at es viejo, recompute.
    """
    topics = await _known_topics(session)
    while len(topics) < TOPIC_SLOTS:
        topics.append(f"__pad_{len(topics)}__")

    # Update article_count first (denormalized)
    await session.execute(
        Author.__table__.update()
        .values(article_count=(
            select(func.count(ArticleAuthor.article_id))
            .where(ArticleAuthor.author_id == Author.id)
            .scalar_subquery()
        ))
    )
    await session.commit()

    candidates = (
        await session.scalars(
            select(Author).where(Author.article_count > 0)
        )
    ).all()

    updated = 0
    now = datetime.now(UTC)
    for author in candidates:
        # Skip si centroid existe y centroid_updated_at < 23h
        if author.centroid is not None and author.centroid_updated_at:
            if (now - author.centroid_updated_at) < timedelta(hours=23):
                continue
        centroid = await _compute_centroid(session, author.id)
        profile = await _compute_profile_vector(session, author.id, topics)
        if centroid is None:
            continue
        author.centroid = centroid
        author.profile_vector = profile
        author.centroid_updated_at = now
        updated += 1

    await session.commit()
    return {"updated": updated, "candidates": len(candidates)}
