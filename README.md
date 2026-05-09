# Noticias

Compara cómo distintos diarios argentinos cubren las mismas noticias.
Pipeline Python (FastAPI) + frontend Next.js + Postgres con pgvector.

## Quickstart

```bash
cp .env.example .env
# editar OPENAI_API_KEY en .env
docker compose up
```

API: http://localhost:8000 · Web: http://localhost:3000

## Estructura

- `api/` — backend Python, pipeline e API REST
- `web/` — frontend Next.js
- `docs/superpowers/` — specs y planes

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
