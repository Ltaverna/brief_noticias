from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.qa.hyde import generate_hypothetical


@pytest.mark.asyncio
async def test_hyde_returns_hypothetical():
    client = MagicMock()
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content="La inflación de abril fue del 4,2%."))]
    client.chat.completions.create = AsyncMock(return_value=fake)

    h = await generate_hypothetical(client, query="cuánto fue la inflación", model="gpt-4o-mini")

    assert h.startswith("La inflación")
    client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_hyde_falls_back_to_query_when_empty():
    client = MagicMock()
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content=""))]
    client.chat.completions.create = AsyncMock(return_value=fake)

    h = await generate_hypothetical(client, query="qué pasó", model="gpt-4o-mini")

    assert h == "qué pasó"


@pytest.mark.asyncio
async def test_hyde_falls_back_to_query_when_whitespace_only():
    client = MagicMock()
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content="   "))]
    client.chat.completions.create = AsyncMock(return_value=fake)

    h = await generate_hypothetical(client, query="qué pasó", model="gpt-4o-mini")

    assert h == "qué pasó"


@pytest.mark.asyncio
async def test_hyde_falls_back_to_query_when_content_is_none():
    client = MagicMock()
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content=None))]
    client.chat.completions.create = AsyncMock(return_value=fake)

    h = await generate_hypothetical(client, query="test query", model="gpt-4o-mini")

    assert h == "test query"


@pytest.mark.asyncio
async def test_hyde_passes_correct_model():
    client = MagicMock()
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content="respuesta hipotética"))]
    client.chat.completions.create = AsyncMock(return_value=fake)

    await generate_hypothetical(client, query="pregunta", model="gpt-4o")

    call_kwargs = client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o"
