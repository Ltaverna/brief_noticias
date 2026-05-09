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
