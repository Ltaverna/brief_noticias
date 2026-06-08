import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from noticias_api.pipeline.analyze import (
    AnalysisResult,
    analyze_cluster,
    select_articles_for_analysis,
)


def _arts(*pairs):
    # pairs: (slug, body) -> minimal article dicts
    return [{"slug": s, "title": f"t-{i}", "body": b} for i, (s, b) in enumerate(pairs)]


def test_select_caps_total_and_per_source():
    # 10 articles from one source; defaults cap per-source at 2.
    arts = _arts(*[("clarin", f"a{i}") for i in range(10)])
    out = select_articles_for_analysis(arts)
    assert len(out) == 2
    assert {a["slug"] for a in out} == {"clarin"}


def test_select_preserves_source_diversity_round_robin():
    # 20 sources, 1 article each, total cap 15 -> 15 distinct sources kept.
    arts = _arts(*[(f"src{i}", "x") for i in range(20)])
    out = select_articles_for_analysis(arts)
    assert len(out) == 15
    assert len({a["slug"] for a in out}) == 15  # one each, no source starved


def test_select_returns_all_when_small():
    arts = _arts(("a", "1"), ("b", "2"), ("a", "3"))
    out = select_articles_for_analysis(arts)
    assert len(out) == 3  # under all caps -> unchanged count


def _mock_openai_response(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@pytest.mark.asyncio
async def test_analyze_cluster_parses_valid_json():
    payload = {
        "headline": "Inflación abril 4,2%",
        "common_facts": ["IPC 4,2%", "Acumulada 142%"],
        "by_source": {
            "la-nacion": {
                "highlights": ["destaca desaceleración"],
                "framing": "positivo para gobierno",
                "tone": "favorable",
            }
        },
        "omissions": [{"source": "la-nacion", "not_mentioned": "alimentos"}],
        "divergences": [{"topic": "causa", "positions": {"la-nacion": "X"}}],
    }
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(json.dumps(payload))
    )

    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "la-nacion", "title": "x", "body": "y"}],
        model="gpt-4o",
    )

    assert isinstance(result, AnalysisResult)
    assert result.headline == "Inflación abril 4,2%"
    assert "IPC 4,2%" in result.common_facts


@pytest.mark.asyncio
async def test_analyze_cluster_retries_on_invalid_json():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response("not json"),
            _mock_openai_response(json.dumps({
                "headline": "x",
                "common_facts": [],
                "by_source": {},
                "omissions": [],
                "divergences": [],
            })),
        ]
    )
    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "x", "title": "t", "body": "b"}],
        model="gpt-4o",
    )
    assert result.headline == "x"
    assert fake_client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_analyze_cluster_returns_none_after_two_failures():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("still not json")
    )
    result = await analyze_cluster(
        fake_client,
        articles=[{"slug": "x", "title": "t", "body": "b"}],
        model="gpt-4o",
    )
    assert result is None
