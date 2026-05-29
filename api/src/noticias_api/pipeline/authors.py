"""Parsing y canonicalización de bylines."""
import re
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Author, AuthorAlias, Source

GENERIC_BYLINES: frozenset[str] = frozenset({
    "redaccion", "redacción", "agencia", "staff", "editorial", "n/a",
})

# Agencias internacionales y nacionales. La detección es por canonical:
# tanto el match exacto como cuando el nombre empieza por una de estas
# (ej "AFP" o "AFP, Reuters" canonicaliza a "afp" o "afp reuters").
KNOWN_AGENCIES: frozenset[str] = frozenset({
    "reuters", "ap", "afp", "telam", "efe", "dpa", "bloomberg", "ansa",
    "associated press",
})

AUTHOR_KINDS: tuple[str, ...] = ("person", "newsroom", "editorial", "agency")


def detect_kind(name: str) -> str:
    """Clasifica un byline en {person, newsroom, editorial, agency}.

    Solo distingue agency vs person aquí. Newsroom y editorial se setean
    explícitamente al crear el sintético (ver ensure_newsroom / ensure_editorial).
    """
    canon = canonicalize_author(name)
    if canon in KNOWN_AGENCIES:
        return "agency"
    # Nombre empieza por una agencia conocida ("AFP corresponsal en Roma")
    first_word = canon.split(" ", 1)[0] if canon else ""
    if first_word in KNOWN_AGENCIES:
        return "agency"
    return "person"

# Substrings (en forma canonicalizada — lowercase sin acentos sin puntuación)
# que indican que el "byline" es en realidad un fragmento de UI o un alias de
# redacción anónima. Cualquier nombre que contenga alguno de estos se descarta.
JUNK_BYLINE_PATTERNS: tuple[str, ...] = (
    "agregar",            # "Agregar Infobae en Google"
    "google",
    "tus medios",
    "seguir en",          # "Seguir en abre en nueva pestaña"
    "nueva pestana",
    "click",
    "cookies",
    "newsroom",           # "Newsroom Infobae" → es alias de redacción
    ".com",               # "Clarin.com - Home"
    "home",
    "portada",
    "http",
)

# Sufijos que delatan al byline como un nombre de redacción del diario
# (ej: "Infobae Noticias", "Clarín Noticias") en vez de una persona real.
JUNK_BYLINE_SUFFIXES: tuple[str, ...] = (
    " noticias",
)

# Cualquier byline más largo que esto es casi seguro UI o un párrafo capturado
# por error, no una persona real.
MAX_BYLINE_LENGTH: int = 60

_PREFIX_RE = re.compile(r"^\s*por\s+", re.IGNORECASE)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_EMAIL_RE = re.compile(r"\S+@\S+")
_SPLIT_RE = re.compile(r"\s+y\s+|,\s*|\s*/\s*|;\s*")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _looks_like_junk(name: str) -> bool:
    """Heurística para detectar bylines que no son personas reales."""
    if len(name) > MAX_BYLINE_LENGTH:
        return True
    canon = canonicalize_author(name)
    if any(pat in canon for pat in JUNK_BYLINE_PATTERNS):
        return True
    if any(canon.endswith(sfx.strip()) for sfx in JUNK_BYLINE_SUFFIXES):
        return True
    return False


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
        if _looks_like_junk(cleaned):
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


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
        await session.flush()
        return existing

    # 3. Crear con ON CONFLICT DO NOTHING para tolerar races con otros
    # procesos que insertan el mismo (canonical, source_id) en paralelo.
    kind = detect_kind(name)
    stmt = (
        pg_insert(Author)
        .values(
            name=name, canonical=canon, source_id=source_id,
            is_synthetic=(kind == "agency"),
            kind=kind,
        )
        .on_conflict_do_nothing(constraint="uq_authors_canon_source")
        .returning(Author.id)
    )
    inserted_id = await session.scalar(stmt)
    if inserted_id is not None:
        return await session.get(Author, inserted_id)

    # Otro proceso ganó la carrera: releemos y devolvemos
    other = await session.scalar(
        select(Author).where(
            Author.canonical == canon, Author.source_id == source_id
        )
    )
    if other:
        other.last_seen_at = datetime.now(UTC)
        return other
    raise RuntimeError(
        f"resolve_author: failed to insert and could not find existing "
        f"({canon!r}, source_id={source_id})"
    )


async def _ensure_synthetic_kind(
    session: AsyncSession, *, source: Source, name: str, kind: str
) -> Author:
    """Helper: idempotente, crea o devuelve un autor sintético del diario con kind dado."""
    canon = canonicalize_author(name)
    existing = await session.scalar(
        select(Author).where(
            Author.canonical == canon,
            Author.source_id == source.id,
        )
    )
    if existing:
        existing.last_seen_at = datetime.now(UTC)
        # Migrar kind si todavía no estaba seteado (autores creados antes de la
        # introducción de kind quedan con 'person' por defecto)
        if existing.kind != kind:
            existing.kind = kind
            existing.is_synthetic = True
        return existing
    stmt = (
        pg_insert(Author)
        .values(
            name=name, canonical=canon, source_id=source.id,
            is_synthetic=True, kind=kind,
        )
        .on_conflict_do_nothing(constraint="uq_authors_canon_source")
        .returning(Author.id)
    )
    inserted_id = await session.scalar(stmt)
    if inserted_id is not None:
        return await session.get(Author, inserted_id)
    other = await session.scalar(
        select(Author).where(
            Author.canonical == canon, Author.source_id == source.id
        )
    )
    if other:
        other.last_seen_at = datetime.now(UTC)
        return other
    raise RuntimeError(
        f"_ensure_synthetic_kind({kind}): race lost and could not find existing "
        f"for source {source.slug}"
    )


async def ensure_synthetic(session: AsyncSession, *, source: Source) -> Author:
    """Idempotente: 'Redacción <source.name>' como autor sintético newsroom.

    Mantenido para compatibilidad con código que ya lo importa.
    """
    return await _ensure_synthetic_kind(
        session, source=source, name=f"Redacción {source.name}", kind="newsroom"
    )


async def ensure_editorial(session: AsyncSession, *, source: Source) -> Author:
    """Idempotente: 'Editorial <source.name>' como autor sintético editorial."""
    return await _ensure_synthetic_kind(
        session, source=source, name=f"Editorial {source.name}", kind="editorial"
    )
