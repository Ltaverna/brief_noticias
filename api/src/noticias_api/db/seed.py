from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Source

SEED_SOURCES: list[dict[str, str]] = [
    {
        "slug": "la-nacion",
        "name": "La Nación",
        "editorial_group": "mainstream",
        "rss_url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
        "base_url": "https://www.lanacion.com.ar",
        "color": "#0f172a",
    },
    {
        "slug": "clarin",
        "name": "Clarín",
        "editorial_group": "mainstream",
        "rss_url": "https://www.clarin.com/rss/lo-ultimo/",
        "base_url": "https://www.clarin.com",
        "color": "#1d4ed8",
    },
    {
        "slug": "infobae",
        "name": "Infobae",
        "editorial_group": "mainstream",
        "rss_url": "https://www.infobae.com/arc/outboundfeeds/rss/",
        "base_url": "https://www.infobae.com",
        "color": "#0ea5e9",
    },
    {
        "slug": "pagina-12",
        "name": "Página 12",
        "editorial_group": "critico",
        "rss_url": "https://www.pagina12.com.ar/arc/outboundfeeds/rss/portada/",
        "base_url": "https://www.pagina12.com.ar",
        "color": "#dc2626",
    },
    {
        "slug": "tiempo-argentino",
        "name": "Tiempo Argentino",
        "editorial_group": "critico",
        "rss_url": "https://www.tiempoar.com.ar/feed/",
        "base_url": "https://www.tiempoar.com.ar",
        "color": "#f59e0b",
    },
    {
        "slug": "el-destape",
        "name": "El Destape",
        "editorial_group": "critico",
        "rss_url": "https://www.eldestapeweb.com/rss/portada.xml",
        "base_url": "https://www.eldestapeweb.com",
        "color": "#7c3aed",
    },
    {
        "slug": "ambito",
        "name": "Ámbito",
        "editorial_group": "economico",
        "rss_url": "https://www.ambito.com/rss/pages/home.xml",
        "base_url": "https://www.ambito.com",
        "color": "#16a34a",
    },
    {
        "slug": "el-cronista",
        "name": "El Cronista",
        "editorial_group": "economico",
        "rss_url": "https://www.cronista.com/arc/outboundfeeds/news/",
        "base_url": "https://www.cronista.com",
        "color": "#0d9488",
    },
    {
        "slug": "bae",
        "name": "BAE Negocios",
        "editorial_group": "economico",
        "rss_url": "https://www.baenegocios.com/files/rss/ultimas-noticias.xml",
        "base_url": "https://www.baenegocios.com",
        "color": "#475569",
    },
]


async def seed_sources(session: AsyncSession) -> int:
    inserted = 0
    for data in SEED_SOURCES:
        existing = await session.scalar(select(Source).where(Source.slug == data["slug"]))
        if existing:
            continue
        session.add(Source(**data))
        inserted += 1
    await session.commit()
    return inserted
