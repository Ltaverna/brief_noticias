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
