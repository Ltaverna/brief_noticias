# Noticias

Compara cómo distintos diarios argentinos cubren las mismas noticias — y dónde divergen.

```
┌─────────────────────────────────────────────────────────────┐
│  Briefing del día                      [Actualizar]         │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Milei cierra acuerdo │  │ INDEC: inflación baja │        │
│  │ 4 diarios · 2 div.   │  │ 7 diarios · 5 div.   │        │
│  │ [política] [Clarín]  │  │ [economía] [Ámbito]  │        │
│  │ [La Nación] [P12]    │  │ [Cronista] [Infobae] │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Por qué existe

Los diarios argentinos cubren los mismos hechos con encuadres, énfasis y omisiones radicalmente distintos. Noticias agrupa automáticamente artículos que tratan el mismo evento, pide a GPT-4o que compare cómo los presenta cada diario, y muestra los resultados en un briefing diario. El objetivo es hacer visible el sesgo editorial sin requerir que el lector lea todos los diarios.

## Diarios cubiertos

| Grupo | Diarios |
|-------|---------|
| Mainstream | La Nación, Clarín, Infobae |
| Crítico | Página 12, Tiempo Argentino, El Destape |
| Económico | Ámbito, El Cronista, BAE Negocios |

## Qué podés hacer

- **Briefing diario**: ver los clusters de noticias del día, filtrados por tema (política, economía, deportes, etc.)
- **Detalle de cluster**: leer hechos en común, el encuadre de cada diario, omisiones y divergencias entre medios
- **Sagas**: seguir historias que se extienden varios días
- **Entidades**: explorar cómo se cubrió una persona, organización o lugar a lo largo del tiempo
- **Q&A conversacional**: preguntas multi-turno con memoria de conversación, HyDE + reranking + CRAG-lite, badge de cobertura y citas numeradas
- **Analytics**: ver tendencias de tono por diario y bias scorecard por entidad
- **Autores**: perfil por autor (notas, clusters, tono, tasa de omisión, divergencia, framing diversity), perfil cualitativo opcional con IA, comparador entre autores, sugerencias de autores parecidos basado en centroide de embeddings + perfil estadístico
- **Suscripciones Telegram**: recibir digest filtrado y alertas cuando una historia cruza N fuentes
- **Bot Telegram**: preguntas libres en lenguaje natural con memoria persistente por chat
- **PWA instalable**: agregar a la pantalla de inicio en iOS y Android
- **Mobile responsive**: navegación hamburger, búsqueda accesible en mobile

## Quickstart

```bash
# 1. Variables de entorno
cp .env.example .env
# Editar: OPENAI_API_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

# 2. Levantar servicios
docker compose up --build

# 3. Migraciones (primera vez)
docker compose exec api alembic upgrade head

# 4. Sembrar fuentes (primera vez)
docker compose exec api python -c "
import asyncio
from noticias_api.db.session import async_session_factory
from noticias_api.db.seed import seed_sources
async def main():
    async with async_session_factory() as s:
        print(await seed_sources(s))
asyncio.run(main())
"

# 5. Abrir la app y correr el pipeline
open http://localhost:3000  # clic en "Actualizar"
```

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, APScheduler |
| Frontend | Next.js 15, React 19, Tailwind 4 |
| Base de datos | Postgres 16 + pgvector |
| LLM | OpenAI (`text-embedding-3-large`, `gpt-4o`, `gpt-4o-mini`) |
| Notificaciones | Telegram Bot API |

## Variables de entorno relevantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Requerido |
| `CRON_HOUR` | `7` | Hora del pipeline automático |
| `CRON_HOURS` | — | Lista CSV para múltiples horas (`7,13,20`) |
| `TOP_N_CLUSTERS` | `20` | Clusters destacados por día |
| `SIMILARITY_THRESHOLD` | `0.70` | Umbral coseno para clustering |
| `MERGE_THRESHOLD` | `0.85` | Umbral para fusionar clusters similares |
| `SAGA_THRESHOLD` | `0.78` | Umbral para agrupar clusters en sagas |
| `ENABLE_TELEGRAM` | `false` | Activar digest y bot |
| `TELEGRAM_BOT_TOKEN` | — | Token del bot |
| `TELEGRAM_CHAT_ID` | — | Chat destino del digest |
| `TELEGRAM_BOT_MODE` | `off` | `webhook` o `polling` |
| `COHERE_API_KEY` | — | Opcional. Activa reranking en Q&A (Cohere v2). Sin él, se usa el top-K del kNN directamente. |
| `ENABLE_HYDE` | `true` | HyDE en el pipeline Q&A |
| `ENABLE_RERANKING` | `true` | Reranking Cohere en Q&A (requiere `COHERE_API_KEY`) |
| `ENABLE_CRAG` | `true` | Evaluación de relevancia por chunk en Q&A |
| `QA_HISTORY_TURNS` | `6` | Turnos de conversación a incluir en el prompt |

## Documentación

| Doc | Descripción |
|-----|-------------|
| [Guía de usuario](docs/user-guide.md) | Cómo usar la interfaz web y el bot |
| [Arquitectura](docs/architecture.md) | Sistema, modelos de datos, pipeline |
| [API Reference](docs/api-reference.md) | Todos los endpoints REST |
| [Development](docs/development.md) | Setup local, tests, convenciones |
| [Deployment](docs/deployment.md) | Raspberry Pi / VPS + Cloudflare Tunnel |

## Tests

```bash
cd api && pytest -v          # 209 tests
cd web && pnpm build         # smoke test del frontend
```

## Backups

```bash
./scripts/backup.sh          # dump + rotación automática
```

Restaurar:

```bash
docker compose exec -T postgres pg_restore -U noticias -d noticias < backups/noticias-XXXX.dump
```

## Licencia

MIT. Contribuciones bienvenidas — abrí un issue o PR.
