from datetime import date, datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import get_settings
from noticias_api.db.models import (
    Analysis, Article, ArticleAuthor, Author, AuthorComparison, AuthorProfile,
    Cluster, ClusterEntity, Entity, Source,
)
from noticias_api.db.session import get_session
from noticias_api.api._aggregations import stats_by_author, stats_by_source_slug
from noticias_api.qa.author_profile import generate_profile
from noticias_api.qa.author_compare import compare_authors

router = APIRouter(tags=["authors"])


def slug_from_canonical(canonical: str) -> str:
    return canonical.replace(" ", "-")


def canonical_from_slug(slug: str) -> str:
    return slug.replace("-", " ")


class AuthorListItem(BaseModel):
    id: int
    name: str
    canonical: str
    slug: str
    source_slug: str | None
    is_synthetic: bool
    article_count: int


class AuthorList(BaseModel):
    authors: list[AuthorListItem]


@router.get("/authors", response_model=AuthorList)
async def list_authors(
    source: str | None = None,
    q: str | None = None,
    order: Annotated[str, Query(pattern="^(articles_desc|last_seen_desc|name_asc)$")] = "articles_desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Author, Source.slug).join(Source, Source.id == Author.source_id, isouter=True)
    if source:
        stmt = stmt.where(Source.slug == source)
    if q:
        stmt = stmt.where(Author.canonical.ilike(f"%{q.lower()}%"))
    if order == "articles_desc":
        stmt = stmt.order_by(Author.article_count.desc())
    elif order == "last_seen_desc":
        stmt = stmt.order_by(Author.last_seen_at.desc())
    else:
        stmt = stmt.order_by(Author.name.asc())
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).all()
    return AuthorList(authors=[
        AuthorListItem(
            id=a.id, name=a.name, canonical=a.canonical,
            slug=slug_from_canonical(a.canonical),
            source_slug=src_slug, is_synthetic=a.is_synthetic,
            article_count=a.article_count or 0,
        )
        for a, src_slug in rows
    ])


async def _author_by_slug(session: AsyncSession, slug: str) -> Author:
    canon = canonical_from_slug(slug)
    author = await session.scalar(
        select(Author).where(Author.canonical == canon).order_by(Author.article_count.desc()).limit(1)
    )
    if not author:
        raise HTTPException(404, f"Author '{slug}' not found")
    return author


@router.get("/authors/{slug}/stats")
async def author_stats(slug: str, session: AsyncSession = Depends(get_session)):
    author = await _author_by_slug(session, slug)
    source = await session.get(Source, author.source_id) if author.source_id else None

    totals = await session.execute(
        select(
            func.count(Article.id).label("articles"),
            func.count(func.distinct(Article.cluster_id)).label("clusters"),
            func.min(Article.published_at).label("first"),
            func.max(Article.published_at).label("last"),
        )
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(ArticleAuthor.author_id == author.id)
    )
    t = totals.one()

    coauth = await session.scalar(
        select(func.count())
        .select_from(ArticleAuthor)
        .where(
            ArticleAuthor.author_id == author.id,
            ArticleAuthor.article_id.in_(
                select(ArticleAuthor.article_id)
                .group_by(ArticleAuthor.article_id)
                .having(func.count() > 1)
            ),
        )
    )

    by_topic_rows = (
        await session.execute(
            select(Cluster.topic, func.count(Article.id))
            .join(Article, Article.cluster_id == Cluster.id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author.id)
            .group_by(Cluster.topic)
            .order_by(func.count(Article.id).desc())
        )
    ).all()
    total = sum(c for _, c in by_topic_rows) or 1
    by_topic = [
        {"topic": tp or "sin-tema", "count": int(c), "share": round(c / total, 3)}
        for tp, c in by_topic_rows
    ]

    by_month_rows = (
        await session.execute(
            select(
                func.to_char(Article.published_at, "YYYY-MM").label("m"),
                func.count(Article.id),
            )
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author.id)
            .where(Article.published_at.isnot(None))
            .group_by("m").order_by("m")
        )
    ).all()
    by_month = [{"month": m, "articles": int(c)} for m, c in by_month_rows]

    top_ents = (
        await session.execute(
            select(Entity.name, Entity.kind, func.count(func.distinct(Cluster.id)))
            .join(ClusterEntity, ClusterEntity.entity_id == Entity.id)
            .join(Cluster, Cluster.id == ClusterEntity.cluster_id)
            .join(Article, Article.cluster_id == Cluster.id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author.id)
            .group_by(Entity.name, Entity.kind)
            .order_by(func.count(func.distinct(Cluster.id)).desc())
            .limit(10)
        )
    ).all()
    top_entities = [
        {"name": n, "kind": k, "clusters": int(c)} for n, k, c in top_ents
    ]

    return {
        "author": {
            "id": author.id, "name": author.name, "canonical": author.canonical,
            "slug": slug_from_canonical(author.canonical),
            "source": source.slug if source else None,
            "is_synthetic": author.is_synthetic,
        },
        "totals": {
            "articles": int(t.articles or 0),
            "clusters": int(t.clusters or 0),
            "coauthored": int(coauth or 0),
            "first_seen": t.first.isoformat() if t.first else None,
            "last_seen": t.last.isoformat() if t.last else None,
        },
        "by_topic": by_topic,
        "by_month": by_month,
        "top_entities": top_entities,
    }


@router.get("/sources/{slug}/byline-coverage")
async def byline_coverage(slug: str, session: AsyncSession = Depends(get_session)):
    src = await session.scalar(select(Source).where(Source.slug == slug))
    if not src:
        raise HTTPException(404, f"Source '{slug}' not found")

    rows = (
        await session.execute(
            select(
                func.to_char(Article.published_at, "YYYY-MM").label("m"),
                Author.is_synthetic,
                func.count(Article.id),
            )
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .join(Author, Author.id == ArticleAuthor.author_id)
            .where(Article.source_id == src.id)
            .where(Article.published_at.isnot(None))
            .group_by("m", Author.is_synthetic)
            .order_by("m")
        )
    ).all()

    by_month: dict[str, dict] = {}
    for m, is_syn, cnt in rows:
        bucket = by_month.setdefault(m, {"month": m, "byline_real": 0, "byline_synthetic": 0})
        if is_syn:
            bucket["byline_synthetic"] += int(cnt)
        else:
            bucket["byline_real"] += int(cnt)
    for v in by_month.values():
        total = v["byline_real"] + v["byline_synthetic"]
        v["coverage"] = round(v["byline_real"] / total, 3) if total else None

    return {"source": slug, "monthly": list(by_month.values())}


@router.get("/authors/{slug}/scorecard")
async def author_scorecard(
    slug: str,
    since: date | None = None,
    until: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    author = await _author_by_slug(session, slug)
    s = await stats_by_author(session, author.id, since=since, until=until)

    baseline = None
    if author.source_id:
        src = await session.get(Source, author.source_id)
        if src:
            base = await stats_by_source_slug(session, src.slug, since=since, until=until)
            if base["n"] > 0 and s["n"] > 0:
                baseline = {
                    "tone_delta": (s["tone_avg"] or 0) - (base["tone_avg"] or 0),
                    "omission_delta": (s["omission_rate"] or 0) - (base["omission_rate"] or 0),
                    "source": src.slug,
                    "n_baseline": base["n"],
                }

    return {
        "n": s["n"],
        "tone": {"avg": s["tone_avg"], "distribution": s["tone_distribution"]},
        "omission_rate": s["omission_rate"],
        "divergence_score": s["divergence_score"],
        "framing_diversity": s["framing_diversity"],
        "vs_source_baseline": baseline,
    }


@router.get("/authors/{slug}/similar")
async def author_similar(
    slug: str,
    weight_topic: float = 0.5,
    weight_profile: float = 0.5,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    session: AsyncSession = Depends(get_session),
):
    author = await _author_by_slug(session, slug)
    if author.centroid is None or author.profile_vector is None:
        return {"similar": [], "reason": "author has no vectors yet"}

    others = (
        await session.execute(
            select(
                Author, Source.slug,
                Author.centroid.cosine_distance(author.centroid).label("d_topic"),
                Author.profile_vector.cosine_distance(author.profile_vector).label("d_profile"),
            )
            .join(Source, Source.id == Author.source_id, isouter=True)
            .where(Author.id != author.id)
            .where(Author.centroid.isnot(None))
            .where(Author.profile_vector.isnot(None))
        )
    ).all()

    scored = []
    for other, src_slug, d_topic, d_profile in others:
        sim_topic = 1.0 - float(d_topic)
        sim_profile = 1.0 - float(d_profile)
        score = weight_topic * sim_topic + weight_profile * sim_profile
        scored.append({
            "slug": slug_from_canonical(other.canonical),
            "name": other.name,
            "source": src_slug,
            "score": round(score, 4),
            "components": {"topic": round(sim_topic, 4), "profile": round(sim_profile, 4)},
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"similar": scored[:limit]}


MIN_SAMPLE_FOR_PROFILE = 3


@router.get("/authors/{slug}/profile")
async def get_author_profile(slug: str, session: AsyncSession = Depends(get_session)):
    author = await _author_by_slug(session, slug)
    profile = await session.get(AuthorProfile, author.id)
    if not profile:
        raise HTTPException(404, "Profile not yet generated")
    return {
        "profile": profile.profile_json,
        "model": profile.model,
        "n_sample": profile.n_sample,
        "generated_at": profile.generated_at.isoformat(),
    }


@router.post("/authors/{slug}/profile/regenerate")
async def regenerate_author_profile(
    slug: str, session: AsyncSession = Depends(get_session),
):
    author = await _author_by_slug(session, slug)
    source = await session.get(Source, author.source_id) if author.source_id else None
    if not source:
        raise HTTPException(400, "Author has no source — cannot generate profile")

    rows = (
        await session.execute(
            select(Analysis)
            .join(Cluster, Cluster.id == Analysis.cluster_id)
            .join(Article, Article.cluster_id == Cluster.id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author.id)
            .order_by(Analysis.generated_at.desc())
            .distinct()
            .limit(30)
        )
    ).scalars().all()

    n = len(rows)
    if n < MIN_SAMPLE_FOR_PROFILE:
        raise HTTPException(
            400,
            f"Muestra insuficiente ({n}/{MIN_SAMPLE_FOR_PROFILE}). "
            "El autor necesita más análisis antes de generar perfil.",
        )

    samples = []
    for a in rows:
        bs = a.by_source or {}
        info = bs.get(source.slug) if isinstance(bs, dict) else None
        framing = info.get("framing") if isinstance(info, dict) else ""
        samples.append({"headline": a.headline or "", "framing": framing or ""})

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    model = settings.chat_model_analysis

    result = await generate_profile(client, model=model, samples=samples, n_sample=n)

    existing = await session.get(AuthorProfile, author.id)
    if existing:
        existing.profile_json = result.model_dump()
        existing.model = model
        existing.n_sample = n
        existing.generated_at = datetime.now(UTC)
    else:
        session.add(AuthorProfile(
            author_id=author.id, profile_json=result.model_dump(),
            model=model, n_sample=n,
        ))
    await session.commit()
    return {"profile": result.model_dump(), "n_sample": n, "model": model}


@router.get("/authors/{slug}/articles")
async def author_articles(
    slug: str,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    session: AsyncSession = Depends(get_session),
):
    author = await _author_by_slug(session, slug)
    arts = (await session.execute(
        select(Article.id, Article.title, Article.url, Article.cluster_id, Article.published_at)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(ArticleAuthor.author_id == author.id)
        .order_by(Article.published_at.desc().nullslast())
        .limit(limit)
    )).all()
    return {"articles": [
        {"id": i, "title": t, "url": u, "cluster_id": c,
         "published_at": p.isoformat() if p else None}
        for i, t, u, c, p in arts
    ]}


class CompareRequest(BaseModel):
    a: str
    b: str
    since: date | None = None
    until: date | None = None


@router.post("/authors/compare")
async def compare_authors_endpoint(
    body: CompareRequest, session: AsyncSession = Depends(get_session),
):
    author_a = await _author_by_slug(session, body.a)
    author_b = await _author_by_slug(session, body.b)
    if author_a.id == author_b.id:
        raise HTTPException(400, "Cannot compare an author with themselves")

    # Canonical order for cache key
    a_id, b_id = sorted([author_a.id, author_b.id])

    overlap_clusters = await session.scalar(
        select(func.count(func.distinct(Article.cluster_id)))
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(ArticleAuthor.author_id == author_a.id)
        .where(Article.cluster_id.in_(
            select(Article.cluster_id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author_b.id)
        ))
    )

    cached = await session.scalar(
        select(AuthorComparison).where(
            AuthorComparison.author_a_id == a_id,
            AuthorComparison.author_b_id == b_id,
            AuthorComparison.since == body.since,
            AuthorComparison.until == body.until,
        )
    )

    stats_a = await stats_by_author(session, author_a.id, since=body.since, until=body.until)
    stats_b = await stats_by_author(session, author_b.id, since=body.since, until=body.until)

    if overlap_clusters == 0:
        return {
            "a": {"slug": body.a, "name": author_a.name},
            "b": {"slug": body.b, "name": author_b.name},
            "overlap_clusters": 0,
            "sintesis": "Los dos autores no tienen cobertura compartida en el periodo seleccionado.",
            "stats_a": stats_a, "stats_b": stats_b,
        }

    if cached:
        return {
            "a": {"slug": body.a, "name": author_a.name},
            "b": {"slug": body.b, "name": author_b.name},
            "overlap_clusters": int(overlap_clusters or 0),
            "cached": True,
            **cached.comparison_json,
        }

    payload = {
        "autor_a": {"nombre": author_a.name, "stats": stats_a},
        "autor_b": {"nombre": author_b.name, "stats": stats_b},
        "overlap_clusters": int(overlap_clusters or 0),
    }
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    model = settings.chat_model_analysis
    result = await compare_authors(client, model=model, payload=payload)

    session.add(AuthorComparison(
        author_a_id=a_id, author_b_id=b_id,
        comparison_json=result.model_dump(),
        model=model, since=body.since, until=body.until,
    ))
    await session.commit()
    return {
        "a": {"slug": body.a, "name": author_a.name},
        "b": {"slug": body.b, "name": author_b.name},
        "overlap_clusters": int(overlap_clusters or 0),
        "cached": False,
        **result.model_dump(),
    }


@router.get("/authors/{slug}/radar")
async def author_radar(slug: str, session: AsyncSession = Depends(get_session)):
    author = await _author_by_slug(session, slug)
    source = await session.get(Source, author.source_id) if author.source_id else None

    # 1. Volume: percentile within source
    if author.source_id:
        p95 = await session.scalar(
            select(func.percentile_cont(0.95).within_group(Author.article_count.asc()))
            .where(Author.source_id == author.source_id)
        ) or 1.0
    else:
        p95 = max(author.article_count or 1, 1)
    volume = min(1.0, (author.article_count or 0) / max(p95, 1.0))

    # 2-5: stats
    s = await stats_by_author(session, author.id)
    tone_raw = s["tone_avg"] or 0.0
    tone = (tone_raw + 1) / 2  # [-1, 1] → [0, 1]
    omission_inv = 1.0 - (s["omission_rate"] or 0.0)
    divergence = s["divergence_score"] or 0.0
    framing_diversity = s["framing_diversity"] or 0.0

    # 6: politics share
    pol = await session.scalar(
        select(func.count(Article.id))
        .join(Cluster, Cluster.id == Article.cluster_id)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .where(ArticleAuthor.author_id == author.id)
        .where(Cluster.topic == "politica")
    ) or 0
    politics_share = (pol / author.article_count) if author.article_count else 0.0

    return {
        "author": {"slug": slug_from_canonical(author.canonical), "name": author.name},
        "source": {"slug": source.slug if source else None,
                   "color": source.color if source else "#94a3b8"},
        "n": s["n"],
        "dimensions": [
            {"key": "volume", "label": "Volumen", "value": round(min(1.0, max(0.0, volume)), 3)},
            {"key": "tone", "label": "Tono", "value": round(min(1.0, max(0.0, tone)), 3)},
            {"key": "no_omission", "label": "Cobertura completa", "value": round(min(1.0, max(0.0, omission_inv)), 3)},
            {"key": "divergence", "label": "Divergencia", "value": round(min(1.0, max(0.0, divergence)), 3)},
            {"key": "framing", "label": "Diversidad framing", "value": round(min(1.0, max(0.0, framing_diversity)), 3)},
            {"key": "politics", "label": "Foco política", "value": round(min(1.0, max(0.0, politics_share)), 3)},
        ],
    }


@router.get("/authors/compare/clusters")
async def shared_clusters(
    a: str, b: str,
    session: AsyncSession = Depends(get_session),
):
    author_a = await _author_by_slug(session, a)
    author_b = await _author_by_slug(session, b)
    rows = (await session.execute(
        select(Cluster.id, Analysis.headline)
        .join(Article, Article.cluster_id == Cluster.id)
        .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
        .join(Analysis, Analysis.cluster_id == Cluster.id, isouter=True)
        .where(ArticleAuthor.author_id == author_a.id)
        .where(Cluster.id.in_(
            select(Article.cluster_id)
            .join(ArticleAuthor, ArticleAuthor.article_id == Article.id)
            .where(ArticleAuthor.author_id == author_b.id)
        ))
        .distinct()
        .order_by(Cluster.last_seen_at.desc())
    )).all()
    return {"clusters": [{"id": cid, "headline": h} for cid, h in rows]}
