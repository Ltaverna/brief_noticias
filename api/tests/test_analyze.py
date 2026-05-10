import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from noticias_api.pipeline.analyze import AnalysisResult, analyze_cluster


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
