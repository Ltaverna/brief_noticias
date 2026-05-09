from unittest.mock import AsyncMock, MagicMock

import pytest

from noticias_api.pipeline.embed import build_embedding_input, embed_texts


def test_build_embedding_input_uses_content_when_available():
    text = build_embedding_input(
        title="Inflación abril",
        content="El INDEC informó " * 100,  # long
        summary="resumen",
    )
    assert text.startswith("Inflación abril\n\n")
    assert "INDEC" in text
    assert "resumen" not in text  # content takes priority


def test_build_embedding_input_falls_back_to_summary():
    text = build_embedding_input(
        title="Boca-River", content=None, summary="El partido fue 2-1."
    )
    assert "Boca-River" in text
    assert "2-1" in text


def test_build_embedding_input_truncates_content():
    long_content = "a" * 10000
    text = build_embedding_input(title="x", content=long_content, summary=None)
    assert len(text) < 2100  # title + sep + 2000 chars max


@pytest.mark.asyncio
async def test_embed_texts_batches_calls():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(3)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_response)

    embeddings = await embed_texts(fake_client, ["a", "b", "c"], model="text-embedding-3-small")

    assert len(embeddings) == 3
    assert all(len(e) == 1536 for e in embeddings)
    fake_client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-3-small", input=["a", "b", "c"]
    )


@pytest.mark.asyncio
async def test_embed_texts_returns_empty_for_empty_input():
    fake_client = MagicMock()
    embeddings = await embed_texts(fake_client, [], model="text-embedding-3-small")
    assert embeddings == []
