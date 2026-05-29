from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import (
    Article, ArticleAuthor, Author, Cluster, ClusterEntity, Entity, Source,
)
from noticias_api.db.session import get_session

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
