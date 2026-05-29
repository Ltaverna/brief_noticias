"""Parsing y canonicalización de bylines."""
import re
import unicodedata

GENERIC_BYLINES: frozenset[str] = frozenset({
    "redaccion", "redacción", "agencia", "staff", "editorial", "n/a",
})

_PREFIX_RE = re.compile(r"^\s*por\s+", re.IGNORECASE)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_EMAIL_RE = re.compile(r"\S+@\S+")
_SPLIT_RE = re.compile(r"\s+y\s+|,\s*|\s*/\s*|;\s*")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _strip_accents(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def canonicalize_author(name: str) -> str:
    """Lowercase, remove accents, strip punctuation, collapse whitespace."""
    s = _strip_accents(name).lower()
    s = _PUNCT_RE.sub(" ", s)
    return " ".join(s.split())


def _clean_name(piece: str) -> str:
    piece = _PAREN_RE.sub(" ", piece)
    piece = _EMAIL_RE.sub(" ", piece)
    return " ".join(piece.split())


def parse_byline(raw: str | None) -> list[str]:
    """Split y limpieza de un campo byline crudo. Devuelve lista sin genéricos."""
    if not raw or not raw.strip():
        return []
    s = _PREFIX_RE.sub("", raw.strip())
    parts = _SPLIT_RE.split(s)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        cleaned = _clean_name(p)
        if not cleaned:
            continue
        if canonicalize_author(cleaned) in GENERIC_BYLINES:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Author, AuthorAlias, Source


async def resolve_author(
    session: AsyncSession, *, name: str, source_id: int
) -> Author:
    """Resuelve un nombre crudo a Author: alias → existente → crea."""
    canon = canonicalize_author(name)
    # 1. Alias?
    alias = await session.scalar(
        select(AuthorAlias).where(AuthorAlias.alias_canonical == canon)
    )
    if alias:
        author = await session.get(Author, alias.author_id)
        if author:
            author.last_seen_at = datetime.now(UTC)
            return author

    # 2. Existente con mismo (canonical, source_id)?
    existing = await session.scalar(
        select(Author).where(
            Author.canonical == canon, Author.source_id == source_id
        )
    )
    if existing:
        existing.last_seen_at = datetime.now(UTC)
        if len(name) > len(existing.name):
            existing.name = name
        return existing

    # 3. Crear
    author = Author(
        name=name, canonical=canon, source_id=source_id,
        is_synthetic=False,
    )
    session.add(author)
    await session.flush()
    return author


async def ensure_synthetic(session: AsyncSession, *, source: Source) -> Author:
    """Idempotente: 'Redacción <source.name>' como autor sintético."""
    name = f"Redacción {source.name}"
    canon = canonicalize_author(name)
    existing = await session.scalar(
        select(Author).where(
            Author.canonical == canon,
            Author.source_id == source.id,
            Author.is_synthetic.is_(True),
        )
    )
    if existing:
        existing.last_seen_at = datetime.now(UTC)
        return existing
    author = Author(
        name=name, canonical=canon, source_id=source.id,
        is_synthetic=True,
    )
    session.add(author)
    await session.flush()
    return author
