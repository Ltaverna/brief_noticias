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
    },
    {
        "slug": "clarin",
        "name": "Clarín",
        "editorial_group": "mainstream",
        "rss_url": "https://www.clarin.com/rss/lo-ultimo/",
        "base_url": "https://www.clarin.com",
    },
    {
        "slug": "infobae",
        "name": "Infobae",
        "editorial_group": "mainstream",
        "rss_url": "https://www.infobae.com/arc/outboundfeeds/rss/",
        "base_url": "https://www.infobae.com",
    },
    {
        "slug": "pagina-12",
        "name": "Página 12",
        "editorial_group": "critico",
        "rss_url": "https://www.pagina12.com.ar/arc/outboundfeeds/rss/portada/",
        "base_url": "https://www.pagina12.com.ar",
    },
    {
        "slug": "tiempo-argentino",
        "name": "Tiempo Argentino",
        "editorial_group": "critico",
        "rss_url": "https://www.tiempoar.com.ar/feed/",
        "base_url": "https://www.tiempoar.com.ar",
    },
    {
        "slug": "el-destape",
        "name": "El Destape",
        "editorial_group": "critico",
        "rss_url": "https://www.eldestapeweb.com/rss/portada.xml",
        "base_url": "https://www.eldestapeweb.com",
    },
    {
        "slug": "ambito",
        "name": "Ámbito",
        "editorial_group": "economico",
        "rss_url": "https://www.ambito.com/rss/pages/home.xml",
        "base_url": "https://www.ambito.com",
    },
    {
        "slug": "el-cronista",
        "name": "El Cronista",
        "editorial_group": "economico",
        "rss_url": "https://www.cronista.com/arc/outboundfeeds/news/",
        "base_url": "https://www.cronista.com",
    },
    {
        "slug": "bae",
        "name": "BAE Negocios",
        "editorial_group": "economico",
        "rss_url": "https://www.baenegocios.com/files/rss/ultimas-noticias.xml",
        "base_url": "https://www.baenegocios.com",
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
