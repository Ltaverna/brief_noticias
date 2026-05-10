from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.qa.retrieval import RetrievedChunk
from noticias_api.qa.synthesis import (
    build_user_prompt,
    parse_citations,
    synthesize,
)


def _chunk(n: int, source: str = "ln") -> RetrievedChunk:
    return RetrievedChunk(
        article_id=n, cluster_id=n, source_slug=source, source_name=source.upper(),
        title=f"title {n}", url=f"https://x/{n}",
        published_at=datetime(2026, 5, 9, tzinfo=UTC),
        text=f"title {n}\nbody about {n}",
        snippet=f"body about {n}",
    )


def test_parse_citations_dedups_in_order():
    assert parse_citations("foo [1] bar [3] baz [1] qux [2]") == [1, 3, 2]


def test_parse_citations_empty():
    assert parse_citations("no citations here") == []


def test_build_user_prompt_numbers_chunks():
    p = build_user_prompt("¿pregunta?", [_chunk(1), _chunk(2)])
    assert "[1] (ln, 2026-05-09)" in p
    assert "[2] (ln, 2026-05-09)" in p
    assert "Pregunta: ¿pregunta?" in p


@pytest.mark.asyncio
async def test_synthesize_returns_answer_and_used_citations():
    client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [
        MagicMock(message=MagicMock(content="La Nación dijo X [1] y Clarín dijo Y [2]."))
    ]
    client.chat.completions.create = AsyncMock(return_value=fake_resp)

    result = await synthesize(
        client, question="qué pasó",
        chunks=[_chunk(1), _chunk(2)],
        model="gpt-4o",
    )
    assert "La Nación" in result.answer
    assert result.used_citations == [1, 2]
