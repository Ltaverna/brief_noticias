"""Tests for CRAG-lite chunk relevance evaluation."""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.qa.crag import (
    EMPTY_ANSWER,
    CragResult,
    evaluate_relevance,
    filter_chunks,
)
from noticias_api.qa.retrieval import RetrievedChunk


def _chunk(n: int) -> RetrievedChunk:
    return RetrievedChunk(
        article_id=n,
        cluster_id=n,
        source_slug=f"src{n}",
        source_name=f"S{n}",
        title=f"title {n}",
        url=f"https://x/{n}",
        published_at=datetime(2026, 5, 9, tzinfo=UTC),
        text=f"body {n}",
        snippet=f"snippet {n}",
    )


def _mock_response(content: str):
    r = MagicMock()
    r.choices = [MagicMock(message=MagicMock(content=content))]
    return r


# ---------------------------------------------------------------------------
# evaluate_relevance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_chunks_returns_empty():
    client = MagicMock()
    res = await evaluate_relevance(
        client, query="x", chunks=[], model="gpt-4o-mini",
    )
    assert res.confidence == "empty"
    assert res.relevant_indices == []
    assert res.ambiguous_indices == []
    # Should not have called the LLM at all
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_confident_when_3_or_more_relevant():
    client = MagicMock()
    payload = {"verdicts": [
        {"n": 1, "verdict": "relevant"},
        {"n": 2, "verdict": "relevant"},
        {"n": 3, "verdict": "relevant"},
        {"n": 4, "verdict": "irrelevant"},
        {"n": 5, "verdict": "ambiguous"},
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 6)],
        model="gpt-4o-mini", min_relevant=3,
    )
    assert res.confidence == "confident"
    assert res.relevant_indices == [1, 2, 3]
    assert res.ambiguous_indices == [5]
    assert res.verdicts[4] == "irrelevant"


@pytest.mark.asyncio
async def test_partial_when_few_relevant():
    client = MagicMock()
    payload = {"verdicts": [
        {"n": 1, "verdict": "relevant"},
        {"n": 2, "verdict": "irrelevant"},
        {"n": 3, "verdict": "irrelevant"},
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 4)],
        model="gpt-4o-mini", min_relevant=3,
    )
    assert res.confidence == "partial"
    assert res.relevant_indices == [1]


@pytest.mark.asyncio
async def test_empty_when_zero_relevant():
    client = MagicMock()
    payload = {"verdicts": [
        {"n": 1, "verdict": "irrelevant"},
        {"n": 2, "verdict": "irrelevant"},
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 3)],
        model="gpt-4o-mini",
    )
    assert res.confidence == "empty"
    assert res.relevant_indices == []


@pytest.mark.asyncio
async def test_parse_failure_falls_back_to_partial_ambiguous():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response("not json at all")
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 4)],
        model="gpt-4o-mini",
    )
    assert res.confidence == "partial"
    assert all(v == "ambiguous" for v in res.verdicts.values())
    assert res.relevant_indices == []
    assert res.ambiguous_indices == [1, 2, 3]


@pytest.mark.asyncio
async def test_unknown_verdicts_default_to_ambiguous():
    client = MagicMock()
    payload = {"verdicts": [
        {"n": 1, "verdict": "relevant"},
        {"n": 2, "verdict": "kinda-relevant"},   # unknown
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 3)],
        model="gpt-4o-mini",
    )
    assert res.verdicts[1] == "relevant"
    assert res.verdicts[2] == "ambiguous"


@pytest.mark.asyncio
async def test_out_of_range_n_is_ignored():
    """Verdicts with n outside [1, len(chunks)] must be silently dropped."""
    client = MagicMock()
    payload = {"verdicts": [
        {"n": 1, "verdict": "relevant"},
        {"n": 99, "verdict": "relevant"},   # out of range — should be ignored
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(1)],
        model="gpt-4o-mini",
    )
    assert 99 not in res.verdicts
    assert res.verdicts[1] == "relevant"


@pytest.mark.asyncio
async def test_missing_chunks_default_to_ambiguous():
    """Chunks the LLM omits from its response must default to ambiguous."""
    client = MagicMock()
    # LLM only returns verdict for chunk 1; chunks 2 and 3 are omitted.
    payload = {"verdicts": [
        {"n": 1, "verdict": "relevant"},
    ]}
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps(payload))
    )
    res = await evaluate_relevance(
        client, query="q",
        chunks=[_chunk(i) for i in range(1, 4)],
        model="gpt-4o-mini",
    )
    assert res.verdicts[2] == "ambiguous"
    assert res.verdicts[3] == "ambiguous"


# ---------------------------------------------------------------------------
# filter_chunks
# ---------------------------------------------------------------------------


def test_filter_chunks_confident_drops_irrelevant():
    chunks = [_chunk(i) for i in range(1, 6)]
    res = CragResult(
        verdicts={1: "relevant", 2: "irrelevant", 3: "relevant", 4: "ambiguous", 5: "irrelevant"},
        confidence="confident",
        relevant_indices=[1, 3],
        ambiguous_indices=[4],
    )
    filtered = filter_chunks(chunks, res)
    titles = {c.title for c in filtered}
    assert titles == {"title 1", "title 3", "title 4"}


def test_filter_chunks_empty_returns_empty_list():
    chunks = [_chunk(i) for i in range(1, 4)]
    res = CragResult(
        verdicts={1: "irrelevant", 2: "irrelevant", 3: "irrelevant"},
        confidence="empty",
        relevant_indices=[],
        ambiguous_indices=[],
    )
    assert filter_chunks(chunks, res) == []


def test_filter_chunks_partial_keeps_top_3_ambiguous():
    """Partial confidence: keep 1 relevant + first 3 ambiguous; 4th ambiguous and irrelevant dropped."""
    chunks = [_chunk(i) for i in range(1, 8)]
    res = CragResult(
        verdicts={1: "relevant", 2: "ambiguous", 3: "ambiguous", 4: "ambiguous", 5: "ambiguous", 6: "irrelevant", 7: "irrelevant"},
        confidence="partial",
        relevant_indices=[1],
        ambiguous_indices=[2, 3, 4, 5],
    )
    filtered = filter_chunks(chunks, res)
    titles = {c.title for c in filtered}
    # 1 (relevant) + first 3 ambiguous (2, 3, 4) = 4 chunks; 5th ambiguous dropped
    assert titles == {"title 1", "title 2", "title 3", "title 4"}
    assert len(filtered) == 4


def test_filter_chunks_confident_keeps_ambiguous():
    """Confident confidence: keep all relevant + all ambiguous."""
    chunks = [_chunk(i) for i in range(1, 6)]
    res = CragResult(
        verdicts={1: "relevant", 2: "ambiguous", 3: "ambiguous", 4: "ambiguous", 5: "irrelevant"},
        confidence="confident",
        relevant_indices=[1],
        ambiguous_indices=[2, 3, 4],
    )
    filtered = filter_chunks(chunks, res)
    titles = {c.title for c in filtered}
    assert "title 5" not in titles
    assert len(filtered) == 4


def test_filter_chunks_preserves_order():
    """Output order must match original chunk order."""
    chunks = [_chunk(i) for i in range(1, 6)]
    res = CragResult(
        verdicts={1: "relevant", 2: "irrelevant", 3: "relevant", 4: "irrelevant", 5: "ambiguous"},
        confidence="confident",
        relevant_indices=[1, 3],
        ambiguous_indices=[5],
    )
    filtered = filter_chunks(chunks, res)
    assert [c.title for c in filtered] == ["title 1", "title 3", "title 5"]


# ---------------------------------------------------------------------------
# EMPTY_ANSWER sanity
# ---------------------------------------------------------------------------


def test_empty_answer_is_nonempty_string():
    assert isinstance(EMPTY_ANSWER, str)
    assert len(EMPTY_ANSWER) > 20
    assert "No encontré" in EMPTY_ANSWER
