import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from noticias_api.pipeline.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class BySource(BaseModel):
    highlights: list[str]
    framing: str
    tone: str


class Omission(BaseModel):
    source: str
    not_mentioned: str


class Divergence(BaseModel):
    topic: str
    positions: dict[str, str]


class AnalysisResult(BaseModel):
    headline: str
    common_facts: list[str]
    by_source: dict[str, BySource]
    omissions: list[Omission]
    divergences: list[Divergence]


# Keep the analysis prompt within the model's per-request / TPM budget.
# Large merged clusters (many sources × articles) otherwise produce 30k+ token
# prompts that the API rejects with a 429 "request too large".
MAX_ARTICLES_PER_ANALYSIS = 15
MAX_ARTICLES_PER_SOURCE = 2


def select_articles_for_analysis(
    articles: list[dict[str, Any]],
    *,
    max_total: int = MAX_ARTICLES_PER_ANALYSIS,
    max_per_source: int = MAX_ARTICLES_PER_SOURCE,
) -> list[dict[str, Any]]:
    """Bound prompt size while keeping source diversity.

    Round-robins across sources so every diario is represented before any
    source contributes a second article, capping per-source and overall.
    Preserves the input order of sources and of articles within a source.
    """
    by_source: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for a in articles:
        slug = a["slug"]
        if slug not in by_source:
            by_source[slug] = []
            order.append(slug)
        by_source[slug].append(a)

    selected: list[dict[str, Any]] = []
    round_i = 0
    while len(selected) < max_total:
        progressed = False
        for slug in order:
            bucket = by_source[slug]
            if round_i < min(len(bucket), max_per_source):
                selected.append(bucket[round_i])
                progressed = True
                if len(selected) >= max_total:
                    break
        if not progressed:
            break
        round_i += 1
    return selected


async def _request(client: AsyncOpenAI, model: str, prompt: str, *, temperature: float) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def analyze_cluster(
    client: AsyncOpenAI,
    *,
    articles: list[dict[str, Any]],
    model: str,
) -> AnalysisResult | None:
    prompt = build_user_prompt(articles)
    for attempt, temp in enumerate([0.3, 0.0]):
        try:
            raw = await _request(client, model, prompt, temperature=temp)
            data = json.loads(raw)
            return AnalysisResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("analyze_cluster attempt %s failed: %s", attempt + 1, exc)
    return None


def prompt_version() -> str:
    return PROMPT_VERSION
