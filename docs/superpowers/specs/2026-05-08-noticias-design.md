# Noticias — Comparador de coberturas de diarios argentinos

**Fecha:** 2026-05-08
**Estado:** Diseño aprobado, pendiente plan de implementación

## 1. Resumen

Web app personal que compara cómo distintos diarios argentinos cubren las mismas noticias. Para cada historia destacada del día, agrupa las notas de varios diarios y produce un análisis estructurado (hechos en común, qué destaca cada diario, omisiones, divergencias y framing). El usuario navega un briefing diario en una interfaz Next.js servida por una API Python.

**Caso de uso:** un solo usuario (el autor) entra al sitio cada mañana para entender qué pasó y, sobre todo, cómo lo están contando los distintos sectores del periodismo argentino.

## 2. Decisiones de producto

| Decisión | Valor |
|----------|-------|
| Consumo | Web app personal (1 usuario) |
| Diarios cubiertos | 9, en 3 grupos editoriales |
| Alcance | Top ~10-20 historias del día |
| Acceso a contenido | Solo material públicamente accesible (RSS + HTML abierto) |
| Formato de salida | Análisis estructurado por IA (hechos comunes, por-diario, omisiones, divergencias) |
| Frecuencia | Cron diario 7am + botón manual de refresh |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Stack | Pipeline Python (FastAPI) + frontend Next.js |
| Persistencia | Postgres único con pgvector |

### 2.1 Diarios cubiertos

- **Mainstream centro-derecha:** La Nación, Clarín, Infobae
- **Crítico / centro-izquierda:** Página 12, Tiempo Argentino, El Destape
- **Económicos / financieros:** Ámbito, El Cronista, BAE

Limitación conocida: La Nación, Clarín, Ámbito y El Cronista tienen paywall duro. Para esos casos se usa título + summary del RSS como fallback (`has_full_text=false`); el análisis pierde detalle pero el cluster queda igual representado.

## 3. Arquitectura general

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  app router · server components · Tailwind · next-themes         │
│  páginas: /, /cluster/[id], /briefing/[date], /historial, /fuentes│
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON
┌────────────────────────────▼────────────────────────────────────┐
│                     Backend Python (FastAPI)                     │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │  REST API        │  │  Pipeline (APScheduler)          │    │
│  │  - GET /clusters │  │  cron 7am + on-demand vía API    │    │
│  │  - GET /cluster  │  │  fetch → parse → embed →         │    │
│  │  - POST /refresh │  │  cluster → rank → analyze →      │    │
│  │  - GET /sources  │  │  persist                         │    │
│  └──────────────────┘  └──────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
┌───────▼──────┐    ┌────────▼────────┐   ┌───────▼──────────┐
│  Postgres    │    │  OpenAI API     │   │  Diarios (RSS +  │
│  + pgvector  │    │  - embeddings   │   │   HTML público)  │
│              │    │  - GPT-4o(-mini)│   │                  │
└──────────────┘    └─────────────────┘   └──────────────────┘
```

**Componentes:**

- `noticias-api/` (Python): FastAPI + pipeline en mismo proceso. APScheduler corre como background task del lifespan de FastAPI.
- `noticias-web/` (Next.js): consume la API por HTTP. Sin lógica de negocio, solo presentación y proxy de `POST /refresh`.
- Postgres único, accedido solo por el backend Python.

**Refresh manual:** botón en UI → Next.js `POST /api/refresh` (proxy) → FastAPI encola pipeline → responde 202 con `run_id` → Next.js polea `GET /runs/:id` para mostrar progreso → al completar, `router.refresh()` re-renderiza el briefing.

## 4. Modelo de datos

5 tablas en Postgres con extensión `pgvector`. Volumen estimado: ~180 articles/día × 365 ≈ 65k/año, ~7k clusters/año.

```sql
sources (
  id              serial primary key,
  slug            text unique not null,        -- 'la-nacion', 'pagina-12'
  name            text not null,
  editorial_group text not null,                -- 'mainstream'|'critico'|'economico'
  rss_url         text not null,
  base_url        text not null,
  enabled         boolean default true
);

articles (
  id             bigserial primary key,
  source_id      int references sources(id),
  external_id    text not null,                 -- guid del RSS o URL
  url            text not null,
  title          text not null,
  summary        text,
  content        text,                          -- texto completo, NULL si paywall
  has_full_text  boolean default false,
  published_at   timestamptz,
  fetched_at     timestamptz default now(),
  embedding      vector(1536),                  -- text-embedding-3-small
  cluster_id     bigint references clusters(id),
  unique(source_id, external_id)
);

clusters (
  id              bigserial primary key,
  centroid        vector(1536),
  first_seen_at   timestamptz default now(),
  last_seen_at    timestamptz default now(),
  article_count   int default 0,
  source_count    int default 0,
  rank_score      float,
  is_top          boolean default false,
  display_date    date
);

analyses (
  id              bigserial primary key,
  cluster_id      bigint references clusters(id) unique,
  headline        text,
  common_facts    jsonb,                        -- ["hecho1", "hecho2"]
  by_source       jsonb,                        -- { slug: { highlights, framing, tone } }
  omissions       jsonb,                        -- [{ source, not_mentioned }]
  divergences     jsonb,                        -- [{ topic, positions: { slug: stance } }]
  model           text,
  prompt_version  text,
  generated_at    timestamptz default now()
);

runs (
  id              bigserial primary key,
  trigger         text not null,                -- 'cron'|'manual'
  status          text not null,                -- 'queued'|'running'|'success'|'partial'|'failed'
  started_at      timestamptz default now(),
  finished_at     timestamptz,
  stats           jsonb,
  error           text
);
```

**Decisiones de modelado:**

- `articles.cluster_id` es mutable: re-clustering al llegar nuevos artículos puede cambiar la asignación. Por eso no es PK compuesta.
- `analyses` 1:1 con cluster. Si la historia evoluciona, se reemplaza la fila. `prompt_version` permite versionar prompts si querés A/B.
- `display_date` en clusters: una historia que se desarrolla 2 días puede aparecer como top en briefings de días distintos.
- Index HNSW sobre `articles.embedding` y `clusters.centroid` para kNN rápido con pgvector.
- Retención: nada se borra automáticamente. El volumen lo permite por años.

## 5. Pipeline

Ejecutado por cron (7am Argentina) o `POST /refresh`. Sincrónico dentro del proceso, con I/O externo en `async` para paralelizar.

### 5.1 Pasos

**1. Fetch RSS** (paralelo, ~10s)

Para cada source habilitada: `httpx.AsyncClient.get(rss_url)` con timeout 10s, retry 1x. Si falla, queda en `runs.stats.errors_per_source` y el pipeline sigue. Parser: `feedparser`.

**2. Dedupe + persist** (~1s)

`INSERT ... ON CONFLICT (source_id, external_id) DO NOTHING`. Filtro temporal: solo items con `published >= now() - 48h`.

**3. Extracción de texto completo** (paralelo, ~30s)

Para artículos nuevos sin `content`: GET la URL, parseo con `trafilatura`. Si extracción < 200 chars → asume paywall, deja `has_full_text=false`. Respeto: User-Agent identificable, robots.txt cacheado, máximo 2 req/s por dominio.

**4. Embeddings** (batch, ~5s)

OpenAI `text-embedding-3-small`. Input: `title + "\n\n" + (content[:2000] || summary)`. Solo artículos sin embedding. Costo ~$0.001/día.

**5. Clustering** (~2s)

Sobre artículos publicados en últimas 48h: para cada artículo nuevo, kNN vía pgvector (`embedding <=> ...` cosine), top 10. Si vecino con similitud `>= 0.78` → unir a su cluster. Si no → crear cluster nuevo. Si "puentea" dos clusters, mergear. Recalcular centroide y stats de los clusters tocados.

**6. Ranking** (~100ms)

Score: `source_count * 2 + log(article_count + 1) - hours_since_last_seen * 0.05`. Top N (default 15) marcados `is_top=true` con `display_date = today`. Filtro mínimo: `source_count >= 2` (sin contraste no hay comparación).

**7. Análisis con GPT-4o** (paralelo, ~30s para 15 clusters)

Solo clusters `is_top` sin `analyses` o cuyo `last_seen_at > analyses.generated_at`. Prompt versionado:

```
Sos un analista de medios argentinos. Te paso N artículos del MISMO HECHO,
publicados por distintos diarios. Devolvé JSON con:

{
  "headline": "titular neutral, 12-15 palabras",
  "common_facts": ["hechos que TODOS reportan"],
  "by_source": {
    "<slug>": {
      "highlights": ["lo que ESTE diario destaca"],
      "framing": "cómo encuadra el hecho (1 oración)",
      "tone": "neutral|crítico|favorable|alarmista|..."
    }
  },
  "omissions": [{"source": "<slug>", "not_mentioned": "qué hechos clave omite"}],
  "divergences": [{
    "topic": "punto en disputa",
    "positions": {"<slug>": "su postura/cita textual breve"}
  }]
}

No inventes citas. Si un dato no está en el texto del diario, no lo atribuyas.
Diarios:
[<slug>] <título>
<contenido>
[<slug>] <título>
<contenido>
...
```

`response_format={"type": "json_object"}`. Validación con Pydantic. Si parseo falla, 1 retry con `temperature=0`. Si vuelve a fallar, `analysis=null` y badge "Reintentar análisis" en UI.

**8. Cierre del run**

Update `runs.status` a `success` o `partial` con `stats` finales.

### 5.2 Costos estimados

- Embeddings: ~$0.001/día
- Análisis GPT-4o: ~$0.05-0.15/run (15 clusters × ~$0.005-0.01)
- Cron diario + 2-3 manuales: ~$5-15/mes

## 6. API REST (FastAPI)

Sin auth (web personal, accesible solo en red local o detrás de reverse proxy con basic auth si se expone).

```
GET  /healthz                      → { status, db, openai_reachable }

GET  /briefings/today              → briefing del día
GET  /briefings/{date}             → briefing histórico (YYYY-MM-DD)
GET  /briefings                    → lista de fechas disponibles (paginado)

GET  /clusters/{id}                → cluster + articles + analysis completo
GET  /clusters/{id}/articles       → articulos del cluster

POST /refresh                      → encola run manual; 202 con { run_id, status }
GET  /runs/{id}                    → estado del run (polling)
GET  /runs?limit=20                → últimos runs (debug)

GET  /sources                      → lista de diarios + estado
PATCH /sources/{slug}              → toggle enabled
```

### 6.1 Forma del briefing

```json
{
  "date": "2026-05-08",
  "generated_at": "2026-05-08T07:12:34Z",
  "clusters": [
    {
      "id": 1234,
      "headline": "Inflación de abril fue del 4,2% según el INDEC",
      "source_count": 7,
      "article_count": 9,
      "sources": ["la-nacion", "clarin", "pagina-12"],
      "rank_score": 14.8,
      "summary": {
        "common_facts": ["IPC 4,2%", "Acumulada 12 meses 142%"],
        "divergence_count": 3
      }
    }
  ]
}
```

Listado liviano (sin análisis completo). El detalle pesado se trae al entrar a `/clusters/{id}`.

### 6.2 Forma del detalle

```json
{
  "id": 1234,
  "headline": "...",
  "first_seen_at": "...",
  "last_seen_at": "...",
  "analysis": {
    "common_facts": [],
    "by_source": { "la-nacion": {} },
    "omissions": [],
    "divergences": [],
    "generated_at": "...",
    "model": "gpt-4o-..."
  },
  "articles": [
    {
      "source": { "slug": "la-nacion", "name": "La Nación", "editorial_group": "mainstream" },
      "title": "...",
      "url": "...",
      "summary": "...",
      "has_full_text": true,
      "published_at": "..."
    }
  ]
}
```

### 6.3 Concurrencia

- Si ya hay run `running` o `queued`, `POST /refresh` devuelve 409 con el `run_id` existente.
- Pipeline corre como `asyncio.create_task` con lock global en proceso. Suficiente para single-instance.

## 7. Frontend (Next.js)

App router, server components por default, client JS solo para el botón de refresh y los tabs del detalle. Tailwind para styling, `next-themes` para dark mode.

### 7.1 Rutas

| Ruta | Componente | Render |
|------|-----------|--------|
| `/` | Home | Server component, briefing del día |
| `/briefing/[date]` | Briefing histórico | Server component, `revalidate: 60` |
| `/cluster/[id]` | Detalle | Server + client island para tabs, `revalidate: 300` |
| `/historial` | Lista de fechas | Server component |
| `/fuentes` | Estado de diarios | Server component, toggle vía PATCH |

### 7.2 Layout y home

- Header sticky: título "Noticias", fecha del briefing, botón "Actualizar", links a /historial y /fuentes.
- Home: cards de top clusters ordenados por `rank_score`. Cada card: headline IA, chips de los diarios (color por editorial group), one-liner ("7 diarios coincidieron en X. 3 puntos de divergencia."), click → detalle.
- Si no hay briefing del día, estado "Briefing no generado todavía" con CTA "Generar ahora".

### 7.3 Detalle de cluster

1. Headline + meta (X diarios, primera/última mención)
2. Hechos en común (bullets)
3. Por diario: tabs o acordeón, panel por source con highlights / framing / tone, color de fondo por editorial group, link al artículo
4. Omisiones (lista clara)
5. Divergencias: tabla compacta, filas = diarios, columnas = posición. Sección clave para visualizar contraste.
6. Artículos fuente (links agrupados por editorial group)

### 7.4 Botón "Actualizar"

Estados: `idle → procesando → idle/error`. Lógica:
1. Click → `POST /api/refresh` (route handler de Next que proxya a FastAPI)
2. Recibe `run_id`, cambia a "Procesando..."
3. Cada 2s: `GET /api/runs/[id]`, muestra fase actual ("Recolectando...", "Analizando 8 historias...")
4. Si `status=success` → `router.refresh()` para revalidar el server component
5. Si `status=failed` → toast con error, vuelve a idle
6. Si recibe 409 al inicio (ya hay run en curso), engancha polling al `run_id` existente (idempotente)

### 7.5 Estilo

- Tipografía serif para headlines, sans para metadata
- Colores por editorial group neutros (no rojo/azul políticos para no sesgar — algo como warm/cool/neutral)
- Mobile-first; tabla de divergencias con scroll horizontal en móvil

### 7.6 Stack del frontend

Next.js 15 (app router) · React 19 · Tailwind CSS 4 · `next-themes`. Sin shadcn/ui ni libs de estado al inicio.

## 8. Manejo de errores y observabilidad

### 8.1 Principios

1. **Falla parcial siempre que se pueda.** Si un diario no responde, los otros 8 generan briefing. Si GPT-4o falla en un cluster, los otros 14 se publican.
2. **Idempotencia.** Re-correr el pipeline el mismo día no duplica datos.
3. **Errores visibles.** Cualquier error queda en `runs.stats.errors_per_source` y se muestra en `/fuentes`.

### 8.2 Catálogo de errores

| Capa | Falla | Respuesta |
|------|-------|-----------|
| RSS fetch | Timeout / 5xx | 1 retry con backoff. Si falla, `errors.<source>.fetch += 1`, sigue. |
| RSS parse | Feed mal formado | Logear excerpt, marcar source sospechosa. Sigue. |
| HTML extract | Paywall / bot block | `has_full_text=false`, usar summary RSS. No es error. |
| HTML extract | DNS / 5xx | Retry 1x, si falla queda sin contenido completo. |
| Embeddings | Rate limit OpenAI | Backoff exponencial (1, 2, 4, 8s). 4 intentos, después run = `partial`. |
| Embeddings | Token limit | Truncar input a 8000 tokens y reintentar. |
| Clustering | Sin embeddings | Skip, `cluster_id=NULL`, reintenta en próximo run. |
| Análisis GPT-4o | JSON inválido | 1 retry con `temperature=0`. Si falla, `analysis=null`, badge UI. |
| Análisis GPT-4o | Rate limit / timeout | Backoff. 3 intentos, después igual que JSON inválido. |
| DB | Connection drop | Healthz pasa a 503; pipeline aborta el run con `status='failed'`. |

### 8.3 Logging y métricas

- Stdlib `logging` formato JSON (orjson). Level INFO en prod, DEBUG en dev.
- Cada paso loguea `{run_id, step, source?, duration_ms, status}`.
- Errores con stack completo en logs; `runs.error` guarda mensaje resumido para UI.
- Vista `/fuentes`: por source, `last_fetched_at`, `articles_24h`, `error_rate_24h`, toggle enabled.
- Vista `/runs` (sin link en nav, accesible por URL): tabla de últimos 20 runs con stats. Para debug.

### 8.4 Alertas

- Cron 7am no completa para 8am → log warning. Sin paging (app personal).
- `error_rate_24h > 50%` por source → flag rojo en `/fuentes`.

### 8.5 Backups y secrets

- `pg_dump` diario rotando 7 días, vía cron del host.
- Secrets en `.env` (no committed): `OPENAI_API_KEY`, `DATABASE_URL`, `INTERNAL_API_TOKEN`. Cargados con Pydantic Settings.

## 9. Testing

| Capa | Qué se testea | Cómo |
|------|---------------|------|
| Parsers RSS por source | title/url/published correctos dado feed XML | Fixtures de feeds reales en `tests/fixtures/feeds/` |
| Trafilatura | Extracción razonable dado HTML guardado | Fixtures HTML por diario; smoke check (longitud, no "Suscribite") |
| Clustering | Mismo evento → mismo cluster; eventos distintos → clusters distintos | Golden set ~30 artículos sobre 5 eventos con embeddings precomputados |
| Ranking | Score consistente | Unit test con mocks |
| API endpoints | Contratos JSON, status codes | `pytest` + `httpx.AsyncClient` in-process; DB de test con `pytest-postgresql` |
| OpenAI calls | Schema del JSON | Mocks en unit tests; un único e2e real (skipped por default) |
| Frontend | Smoke: páginas renderizan con data mock | Playwright básico contra API mockeada |

No apuntar a 100% coverage. Apuntar a lo que más duele si rompe: parsers (cambio de formato del diario), clustering (regresión silenciosa), schema del análisis (cambio de prompt).

## 10. Estructura del repo

```
noticias/
├── api/
│   ├── pyproject.toml
│   ├── src/noticias_api/
│   │   ├── main.py                   # FastAPI app + lifespan
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── db/
│   │   │   ├── models.py             # SQLAlchemy
│   │   │   └── migrations/           # Alembic
│   │   ├── pipeline/
│   │   │   ├── runner.py
│   │   │   ├── fetch.py
│   │   │   ├── extract.py
│   │   │   ├── embed.py
│   │   │   ├── cluster.py
│   │   │   ├── rank.py
│   │   │   └── analyze.py
│   │   ├── api/
│   │   │   ├── briefings.py
│   │   │   ├── clusters.py
│   │   │   ├── runs.py
│   │   │   └── sources.py
│   │   └── scheduler.py
│   └── tests/
├── web/
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx
│   │   ├── briefing/[date]/page.tsx
│   │   ├── cluster/[id]/page.tsx
│   │   ├── historial/page.tsx
│   │   ├── fuentes/page.tsx
│   │   └── api/
│   │       ├── refresh/route.ts
│   │       └── runs/[id]/route.ts
│   ├── components/
│   │   ├── ClusterCard.tsx
│   │   ├── DivergenceTable.tsx
│   │   ├── SourceChip.tsx
│   │   └── RefreshButton.tsx
│   └── lib/api.ts
├── docker-compose.yml
├── docs/superpowers/specs/
│   └── 2026-05-08-noticias-design.md
└── README.md
```

## 11. Deployment

### 11.1 Local

`docker-compose up` levanta:

- `postgres`: imagen `pgvector/pgvector:pg16`
- `api`: build del Dockerfile Python, expone 8000
- `web`: build del Dockerfile Next, expone 3000

Variables en `.env` raíz. Volumen para datos de Postgres.

### 11.2 Migraciones

Alembic. `alembic upgrade head` corre al startup del container `api`, idempotente.

### 11.3 Deploy a VPS (futuro, opcional)

Mismo `docker-compose`, detrás de Caddy con HTTPS automático y basic auth si va a internet. Cron del host hace `pg_dump` diario.

## 12. Out of scope (por ahora)

- Multi-usuario, auth, roles
- Búsqueda full-text dentro de la app
- Filtros por tema o categoría
- Notificaciones push / email digest
- App móvil nativa
- Manejo de suscripciones / cookies por diario para superar paywalls
- Análisis histórico de tendencias o sentiment a lo largo del tiempo
- Comparación cross-cluster ("¿cómo cubrió cada diario las elecciones de los últimos 3 meses?")

Cualquiera de estos puede ser una iteración futura sobre la base ya construida.
