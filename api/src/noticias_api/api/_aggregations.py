"""Agregaciones reusables para analytics por diario, entidad o autor.

Parametrizan el "group by" sobre los mismos campos JSONB de Analysis.by_source.
"""
import unicodedata
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import (
    Analysis,
    Article,
    ArticleAuthor,
    Cluster,
    Source,
)

TONES = ["favorable", "celebratorio", "neutral", "critico", "esceptico", "alarmista", "otro"]


def normalize_tone(raw: str | None) -> str:
    if not raw:
        return "otro"
    s = raw.strip().lower()
    s = "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )
    return s if s in TONES else "otro"


def tone_to_numeric(tone: str) -> float:
    """Map tone to [-1, 1]."""
    mapping = {
        "favorable": 0.7, "celebratorio": 1.0,
        "neutral": 0.0,
        "critico": -0.7, "esceptico": -0.5, "alarmista": -1.0,
        "otro": 0.0,
    }
    return mapping.get(tone, 0.0)


def utc_window(since: date | None, until: date | None) -> tuple[datetime, datetime]:
    now_utc = datetime.now(UTC)
    until_dt = (
        datetime.combine(until, datetime.max.time(), tzinfo=UTC)
        if until else now_utc
    )
    if since is None:
        since_dt = now_utc - timedelta(days=30)
    else:
        since_dt = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
    return since_dt, until_dt


async def stats_by_author(
    session: AsyncSession, author_id: int,
    since: date | None = None, until: date | None = None,
) -> dict:
    """Devuelve tone avg, omission_rate, divergence_score, framing_diversity, n."""
    since_dt, until_dt = utc_window(since, until)

    # Diario del autor (para indexar by_source[slug])
    author_source = await session.scalar(
        select(Source.slug)
        .join(Article, Article.source_id == Source.id)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(ArticleAuthor.author_id == author_id)
        .limit(1)
    )

    rows = (
        await session.execute(
            select(Analysis)
            .join(Cluster, Cluster.id == Analysis.cluster_id)
            .join(Article, Article.cluster_id == Cluster.id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author_id)
            .where(Cluster.last_seen_at >= since_dt)
            .where(Cluster.last_seen_at <= until_dt)
            .distinct()
        )
    ).scalars().all()

    n = len(rows)
    if n == 0:
        return {
            "n": 0, "tone_avg": None, "tone_distribution": {},
            "omission_rate": None, "divergence_score": None,
            "framing_diversity": None,
        }

    tones: list[float] = []
    tone_dist: dict[str, int] = defaultdict(int)
    framings: set[str] = set()
    omissions_count = 0
    divergences_count = 0
    facts_total = 0

    for analysis in rows:
        bs = analysis.by_source or {}
        info = bs.get(author_source) if author_source else None
        if isinstance(info, dict):
            t = normalize_tone(info.get("tone"))
            tones.append(tone_to_numeric(t))
            tone_dist[t] += 1
            framing = info.get("framing") or info.get("encuadre")
            if framing:
                framings.add(str(framing).strip().lower()[:80])
        for om in analysis.omissions or []:
            if isinstance(om, dict) and author_source in (om.get("by") or []):
                omissions_count += 1
        for dv in analysis.divergences or []:
            if isinstance(dv, dict) and author_source in (dv.get("by") or []):
                divergences_count += 1
        facts_total += len(analysis.common_facts or [])

    tone_avg = sum(tones) / len(tones) if tones else None
    omission_rate = omissions_count / max(facts_total, 1) if facts_total else None
    divergence_rate = divergences_count / n
    framing_diversity = len(framings) / n

    return {
        "n": n,
        "tone_avg": tone_avg,
        "tone_distribution": dict(tone_dist),
        "omission_rate": omission_rate,
        "divergence_score": divergence_rate,
        "framing_diversity": framing_diversity,
    }


async def stats_by_source_slug(
    session: AsyncSession, source_slug: str,
    since: date | None = None, until: date | None = None,
) -> dict:
    """Mismo shape que stats_by_author, agregado a nivel diario completo."""
    since_dt, until_dt = utc_window(since, until)
    rows = (
        await session.execute(
            select(Analysis)
            .join(Cluster, Cluster.id == Analysis.cluster_id)
            .where(Cluster.last_seen_at >= since_dt)
            .where(Cluster.last_seen_at <= until_dt)
        )
    ).scalars().all()

    n = 0
    tones: list[float] = []
    omissions_count = 0
    facts_total = 0
    divergences_count = 0
    framings: set[str] = set()

    for analysis in rows:
        bs = analysis.by_source or {}
        info = bs.get(source_slug)
        if not isinstance(info, dict):
            continue
        n += 1
        t = normalize_tone(info.get("tone"))
        tones.append(tone_to_numeric(t))
        framing = info.get("framing") or info.get("encuadre")
        if framing:
            framings.add(str(framing).strip().lower()[:80])
        for om in analysis.omissions or []:
            if isinstance(om, dict) and source_slug in (om.get("by") or []):
                omissions_count += 1
        for dv in analysis.divergences or []:
            if isinstance(dv, dict) and source_slug in (dv.get("by") or []):
                divergences_count += 1
        facts_total += len(analysis.common_facts or [])

    if n == 0:
        return {"n": 0, "tone_avg": None, "omission_rate": None,
                "divergence_score": None, "framing_diversity": None}

    return {
        "n": n,
        "tone_avg": sum(tones) / len(tones) if tones else None,
        "omission_rate": omissions_count / max(facts_total, 1),
        "divergence_score": divergences_count / n,
        "framing_diversity": len(framings) / n,
    }
