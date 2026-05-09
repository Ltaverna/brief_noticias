# Noticias

Compara cómo distintos diarios argentinos cubren las mismas noticias.
Pipeline Python (FastAPI) + frontend Next.js + Postgres con pgvector.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, APScheduler
- **Frontend:** Next.js 15, React 19, Tailwind 4, next-themes
- **DB:** Postgres 16 + pgvector
- **LLM:** OpenAI (embeddings + GPT-4o)

## Diarios cubiertos

- Mainstream: La Nación, Clarín, Infobae
- Crítico: Página 12, Tiempo Argentino, El Destape
- Económico: Ámbito, El Cronista, BAE Negocios

## Quickstart

1. Copiar y editar variables:

   ```bash
   cp .env.example .env
   # editar OPENAI_API_KEY
   ```

2. Levantar todo:

   ```bash
   docker compose up --build
   ```

3. Aplicar migraciones (la primera vez):

   ```bash
   docker compose exec api alembic upgrade head
   ```

4. Sembrar fuentes (la primera vez):

   ```bash
   docker compose exec api python -c "
   import asyncio
   from noticias_api.db.session import async_session_factory
   from noticias_api.db.seed import seed_sources
   async def main():
       async with async_session_factory() as s:
           print(await seed_sources(s))
   asyncio.run(main())
   "
   ```

5. Visitar http://localhost:3000 — tocar **Actualizar** para correr el pipeline manualmente.

## Estructura

- `api/` — backend Python
- `web/` — frontend Next.js
- `scripts/` — backups y utilidades
- `docs/superpowers/` — specs y planes

## Configuración relevante (.env)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | API key de OpenAI (requerido) |
| `CRON_HOUR` | 7 | Hora del cron diario |
| `TOP_N_CLUSTERS` | 15 | Cuántas historias destacar por día |
| `SIMILARITY_THRESHOLD` | 0.78 | Umbral coseno para clustering |

## Backups

Una corrida del script genera un dump y rota archivos viejos:

```bash
./scripts/backup.sh
```

Para correr automáticamente, agregar al crontab del host:

```
0 4 * * * cd /path/to/noticias && ./scripts/backup.sh >> /var/log/noticias-backup.log 2>&1
```

Restaurar:

```bash
docker compose exec -T postgres pg_restore -U noticias -d noticias < backups/noticias-XXXX.dump
```

## Tests

API:

```bash
cd api && pytest -v
```

Frontend (build smoke):

```bash
cd web && pnpm build
```
