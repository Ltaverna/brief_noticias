import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.pipeline.topic import classify_topic, TOPICS


def _mock_response(content: str):
    r = MagicMock()
    r.choices = [MagicMock(message=MagicMock(content=content))]
    return r


@pytest.mark.asyncio
async def test_classify_returns_known_topic():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps({"topic": "politica"}))
    )
    t = await classify_topic(
        client, headline="Bullrich apretó a Adorni",
        common_facts=["x"], model="gpt-4o-mini",
    )
    assert t == "politica"


@pytest.mark.asyncio
async def test_classify_normalizes_unknown_to_otros():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response(json.dumps({"topic": "ufología"}))
    )
    t = await classify_topic(
        client, headline="x", common_facts=[], model="gpt-4o-mini",
    )
    assert t == "otros"


@pytest.mark.asyncio
async def test_classify_returns_none_on_parse_failures():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_mock_response("not json")
    )
    t = await classify_topic(
        client, headline="x", common_facts=[], model="gpt-4o-mini",
    )
    assert t is None


@pytest.mark.asyncio
async def test_classify_returns_none_for_empty_headline():
    client = MagicMock()
    t = await classify_topic(
        client, headline="", common_facts=[], model="gpt-4o-mini",
    )
    assert t is None


def test_topic_constants_match_known_categories():
    assert "politica" in TOPICS
    assert "economia" in TOPICS
    assert "deportes" in TOPICS
    assert "otros" in TOPICS
