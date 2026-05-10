import httpx
import pytest

from noticias_api.qa.rerank import RerankResult, rerank_with_cohere


@pytest.mark.asyncio
async def test_rerank_calls_cohere(respx_mock):
    respx_mock.post("https://api.cohere.com/v2/rerank").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.5},
                ]
            },
        )
    )

    out = await rerank_with_cohere(
        api_key="sk-test",
        query="x",
        documents=["a", "b", "c"],
        top_n=2,
    )

    assert len(out) == 2
    assert out[0].index == 2
    assert out[0].relevance_score == pytest.approx(0.9)
    assert out[1].index == 0


@pytest.mark.asyncio
async def test_rerank_empty_docs_returns_empty():
    out = await rerank_with_cohere(api_key="sk-test", query="x", documents=[])
    assert out == []


@pytest.mark.asyncio
async def test_rerank_raises_on_non_200(respx_mock):
    respx_mock.post("https://api.cohere.com/v2/rerank").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    with pytest.raises(httpx.HTTPStatusError):
        await rerank_with_cohere(
            api_key="bad-key",
            query="q",
            documents=["doc1", "doc2"],
        )


@pytest.mark.asyncio
async def test_rerank_result_is_frozen():
    r = RerankResult(index=0, relevance_score=0.8)
    with pytest.raises(Exception):
        r.index = 1  # type: ignore[misc]


@pytest.mark.asyncio
async def test_rerank_top_n_capped_to_doc_count(respx_mock):
    """top_n should be min(top_n, len(documents)) in the request payload."""
    captured_body: dict = {}

    async def capture(request):
        import json
        captured_body.update(json.loads(request.content))
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.9}]})

    respx_mock.post("https://api.cohere.com/v2/rerank").mock(side_effect=capture)

    await rerank_with_cohere(
        api_key="sk",
        query="q",
        documents=["only one doc"],
        top_n=10,
    )

    assert captured_body["top_n"] == 1  # min(10, 1)
