"""Backfill author bylines for articles persisted before this feature existed.

Usage:
  docker compose exec api python /app/scripts/backfill_authors.py --limit 200 --rate-limit 1.0
"""
import argparse
import asyncio
import sys
from pathlib import Path

import httpx

# Ensure the api/src path is importable when invoked from repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api" / "src"))

from sqlalchemy import select  # noqa: E402

from noticias_api.config import get_settings  # noqa: E402
from noticias_api.db.models import Article, ArticleAuthor  # noqa: E402
from noticias_api.db.session import async_session_factory  # noqa: E402
from noticias_api.pipeline.extract import extract_content  # noqa: E402
from noticias_api.pipeline.persist import persist_authors_from_html  # noqa: E402


async def main(limit: int, rate_limit: float) -> None:
    settings = get_settings()
    user_agent = getattr(settings, "user_agent", "noticias-bot/0.1")
    async with async_session_factory() as session:
        rows = (await session.execute(
            select(Article)
            .where(Article.has_full_text.is_(True))
            .where(~Article.id.in_(select(ArticleAuthor.article_id)))
            .limit(limit)
        )).scalars().all()
        print(f"Processing {len(rows)} articles...")

        async with httpx.AsyncClient(headers={"User-Agent": user_agent}) as http:
            for i, art in enumerate(rows):
                result = await extract_content(http, art.url)
                if result.authors:
                    await persist_authors_from_html(
                        session, article=art, authors_from_html=result.authors
                    )
                    await session.commit()
                    print(f"[{i+1}/{len(rows)}] {art.url} -> {result.authors}")
                else:
                    print(f"[{i+1}/{len(rows)}] {art.url} -> no authors")
                if rate_limit > 0:
                    await asyncio.sleep(rate_limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--rate-limit", type=float, default=1.0,
                        help="Segundos de pausa entre artículos")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.rate_limit))
