# Guía de desarrollo

Para modificar, extender o depurar el sistema. Para setup de producción, ver [deployment.md](deployment.md).

---

## Setup local

### Requisitos

- Python 3.12
- Node.js 20+ y pnpm 9+
- Docker Compose (para Postgres)
- `OPENAI_API_KEY`

### Backend

```bash
# 1. Levantar solo Postgres en Docker
docker compose up postgres -d

# 2. Crear virtualenv e instalar dependencias
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Variables de entorno
cp ../.env.example .env
# Editar DATABASE_URL para apuntar a localhost:5432

# 4. Migraciones
alembic upgrade head

# 5. Sembrar fuentes
python -c "
import asyncio
from noticias_api.db.session import async_session_factory
from noticias_api.db.seed import seed_sources
async def main():
    async with async_session_factory() as s:
        print(await seed_sources(s))
asyncio.run(main())
"

# 6. Levantar la API
uvicorn noticias_api.main:app --reload --port 8000
```

### Frontend

```bash
cd web
pnpm install

# Variables de entorno
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "INTERNAL_API_URL=http://localhost:8000" >> .env.local

pnpm dev          # http://localhost:3000
```

---

## Tests

### Correr la suite completa

```bash
cd api
pytest -v
```

209 tests, todos async (pytest-asyncio con `asyncio_mode = "auto"`).

### Estructura de tests

```
api/tests/
├── conftest.py           -- fixtures globales
├── test_fetch.py         -- parsing de RSS
├── test_embed.py         -- construcción del input de embedding
├── test_cluster.py       -- algoritmo de clustering y merge
├── test_saga.py          -- asignación de sagas
├── test_analyze.py       -- análisis GPT (mockeado)
├── test_entities.py      -- extracción y canonicalización de entidades
├── test_topic.py         -- clasificación de temas
├── test_rank.py          -- ranking de clusters
├── test_persist.py       -- idempotencia de persist_items
├── test_qa_*.py          -- tests del pipeline RAG (HyDE, rerank, CRAG, historial)
├── test_api_*.py         -- tests de endpoints REST
└── test_notifiers_*.py   -- tests del digest y alertas
```

### Fixtures principales (conftest.py)

```python
@pytest.fixture
async def db_session(postgresql):
    # Base de datos PostgreSQL temporal (pytest-postgresql)
    # Aplica todas las migraciones antes de cada test
    ...

@pytest.fixture
async def client(db_session):
    # TestClient de FastAPI con la sesión de test inyectada
    ...

@pytest.fixture
def respx_mock():
    # Mock de httpx para aislar llamadas HTTP externas (RSS, OpenAI)
    ...
```

### Tests de integración vs unitarios

- Tests de **pipeline** (cluster, merge, saga, rank): usan `db_session` real (Postgres temporal).
- Tests de **API**: usan `client` que inyecta la sesión de test.
- Tests de **fetch/embed/analyze**: usan `respx_mock` para aislar llamadas externas.

### Correr un test específico

```bash
pytest tests/test_cluster.py -v
pytest tests/test_api_briefings.py::test_today_empty -v
```

---

## Working with the RAG pipeline

El pipeline de Q&A vive en `api/src/noticias_api/api/qa.py`. Los pasos en orden:

```
HyDE → embed → kNN (pgvector) → rerank (Cohere) → CRAG → cargar historial → síntesis (GPT-4o) → persistir en qa_messages
```

### Flags de configuración (config.py)

| Flag | Default | Descripción |
|------|---------|-------------|
| `enable_hyde` | `True` | Generar texto hipotético antes de embedear la query |
| `enable_reranking` | `True` | Aplicar Cohere rerank sobre los candidatos del kNN |
| `enable_crag` | `True` | Evaluar relevancia por chunk antes de sintetizar |
| `qa_history_turns` | `6` | Turnos anteriores a incluir en el prompt |
| `cohere_api_key` | `None` | Si es `None`, el reranking se omite sin error |
| `hyde_model` | `"gpt-4o-mini"` | Modelo para generar la respuesta hipotética |
| `rerank_model` | `"rerank-multilingual-v3.0"` | Modelo de Cohere para reranking |
| `rerank_initial_k` | `50` | Candidatos kNN enviados al reranker |
| `rerank_top_k` | `10` | Chunks que pasan del reranker a CRAG/síntesis |
| `crag_model` | `"gpt-4o-mini"` | Modelo para los veredictos de relevancia |
| `crag_min_relevant` | `3` | Chunks relevantes mínimos para nivel "confident" |

Para desactivar un paso en desarrollo, setearlo en `False` en el `.env` (o en el `Settings` object directamente en tests):

```python
# Desactivar reranking localmente sin COHERE_API_KEY
ENABLE_RERANKING=false
```

### COHERE_API_KEY es opcional

Si la variable no está seteada (o `enable_reranking=False`), el sistema usa directamente los primeros `rerank_top_k` resultados del kNN sin llamar a Cohere. La degradación es silenciosa: `crag_verdicts` y `confidence` siguen funcionando igual sobre los candidatos del kNN.

Para testear con reranking real en desarrollo, agregar al `.env`:

```
COHERE_API_KEY=tu_key_aqui
```

### Agregar un nuevo paso al pipeline RAG

El lugar correcto es `api/src/noticias_api/api/qa.py`, dentro de la función de orquestación principal. El patrón general:

```python
# 1. El paso recibe los chunks actuales y las settings
async def mi_paso_rag(
    chunks: list[RetrievedChunk],
    query: str,
    settings: Settings,
    client: AsyncOpenAI,
) -> list[RetrievedChunk]:
    if not settings.enable_mi_paso:
        return chunks
    # ... lógica ...
    return chunks_filtrados

# 2. Wiring en la función principal de qa.py
chunks = await mi_paso_rag(chunks, query, settings, client)
```

Agregar el flag de activación en `config.py` (`enable_mi_paso: bool = True`) y en `.env.example`.

### Testear pasos RAG con mocks

Los tests en `test_qa_*.py` mockean OpenAI y Cohere con `respx` (HTTP) o `unittest.mock`. El patrón común:

```python
# Mockear la llamada de HyDE (chat completion)
with respx.mock:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "respuesta hipotética..."}}]
        })
    )
    result = await qa_endpoint(QARequest(query="¿qué pasó?"), session=db_session, settings=settings)
    assert result.confidence in ("confident", "partial", "empty")
```

Para testear la integración completa con `db_session`, ver los fixtures en `conftest.py` — la DB de test tiene los mismos embeddings fake que el resto de la suite.

### Patrón conversation_id

| Cliente | Formato | Generado por |
|---------|---------|-------------|
| Web | UUID v4 (ej: `a1b2c3d4-...`) | `web/lib/qa-session.ts` en el primer mensaje |
| Bot Telegram | `telegram:{chat_id}` | `bot_handler.py` — hard-coded por chat |

El `conversation_id` llega en el body de `POST /qa`. Si se omite, la API genera uno nuevo y lo retorna en la respuesta. El frontend lo persiste en `localStorage["noticias:qa-conversation"]`.

---

## Agregar un paso al pipeline

El pipeline secuencial está en `api/src/noticias_api/pipeline/runner.py`.

### 1. Crear el módulo

```python
# api/src/noticias_api/pipeline/mi_paso.py

async def mi_paso(session: AsyncSession, ...) -> dict[str, int]:
    """Descripción del paso."""
    # lógica
    return {"procesados": n}
```

### 2. Agregar a RunStats

```python
# runner.py — clase RunStats
@dataclass
class RunStats:
    ...
    mi_paso_count: int = 0

    def dump(self) -> dict:
        return {
            ...,
            "mi_paso_count": self.mi_paso_count,
        }
```

### 3. Invocar desde run_pipeline

```python
# runner.py — función run_pipeline
from noticias_api.pipeline.mi_paso import mi_paso

# después del paso anterior
mi_stats = await mi_paso(session, ...)
stats.mi_paso_count = mi_stats.get("procesados", 0)
```

### 4. Escribir tests

```python
# tests/test_mi_paso.py
import pytest
from noticias_api.pipeline.mi_paso import mi_paso

@pytest.mark.asyncio
async def test_mi_paso_basico(db_session):
    # insertar datos de prueba
    ...
    result = await mi_paso(db_session, ...)
    assert result["procesados"] > 0
```

---

## Agregar un endpoint

La API usa FastAPI con routers por dominio en `api/src/noticias_api/api/`.

### 1. Crear o abrir el router correspondiente

```python
# api/src/noticias_api/api/mi_recurso.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from noticias_api.db.session import get_session

router = APIRouter(tags=["mi-recurso"])

class MiRecursoOut(BaseModel):
    id: int
    nombre: str

@router.get("/mi-recurso/{id}", response_model=MiRecursoOut)
async def get_mi_recurso(id: int, session: AsyncSession = Depends(get_session)):
    ...
```

### 2. Registrar el router en main.py

```python
# api/src/noticias_api/main.py
from noticias_api.api import mi_recurso

app.include_router(mi_recurso.router)
```

### 3. Documentar en api-reference.md

Agregar el endpoint a [api-reference.md](api-reference.md) con método, path, params, body y response de ejemplo.

---

## Agregar una página frontend

El frontend usa Next.js 15 App Router. Todos los componentes de página están en `web/app/`.

### Convención de archivos

```
web/app/
├── mi-seccion/
│   ├── page.tsx          -- Server Component (default)
│   └── [id]/
│       └── page.tsx      -- Server Component con param dinámico
```

### Server Components vs Client Components

- **Server Component (default)**: puede hacer `fetch` directo a la API. No usa hooks de React.
- **Client Component** (`"use client"` al tope): tiene interactividad (formularios, estado local, efectos).

```typescript
// Server Component — renderiza en el servidor
import { api } from "@/lib/api";

export const dynamic = "force-dynamic"; // sin cache en CDN, siempre fresh

export default async function MiPagina() {
  const data = await api.getMiRecurso();
  return <div>{data.nombre}</div>;
}
```

```typescript
// Client Component
"use client";

import { useState } from "react";

export default function MiPaginaInteractiva() {
  const [valor, setValor] = useState("");
  return <input value={valor} onChange={e => setValor(e.target.value)} />;
}
```

### Agregar un call a la API

```typescript
// web/lib/api.ts — agregar al objeto api
getMiRecurso: (id: number): Promise<MiRecurso> =>
  get(`/mi-recurso/${id}`, { next: { revalidate: 120 } }),
```

```typescript
// web/lib/types.ts — agregar la interfaz
export interface MiRecurso {
  id: number;
  nombre: string;
}
```

### `force-dynamic`

Agregar `export const dynamic = "force-dynamic"` a páginas que muestran datos en tiempo real (briefing del día, runs, subscriptions). Páginas de historial o detalle pueden usar `revalidate`.

### Proxy routes

Para evitar CORS en llamadas POST del browser (Q&A, suscripciones), el frontend tiene route handlers en `web/app/api/`:

```typescript
// web/app/api/qa/route.ts
export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${process.env.INTERNAL_API_URL}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return new Response(await res.text(), { status: res.status });
}
```

---

## Migraciones de base de datos

El proyecto usa Alembic con migraciones versionadas en `api/src/noticias_api/db/migrations/versions/`.

### Convención de nombres

```
0001_initial_schema.py
0002_deliveries.py
0003_fts.py
...
0008_cluster_notes.py
```

Número secuencial de 4 dígitos seguido de nombre descriptivo en snake_case.

### Workflow

```bash
# En api/ con el virtualenv activado y DATABASE_URL apuntando a la DB

# Generar una migración automática (basada en cambios en models.py)
alembic revision --autogenerate -m "descripcion"

# Revisar el archivo generado en versions/ antes de aplicar

# Aplicar migraciones pendientes
alembic upgrade head

# Ver estado actual
alembic current

# Rollback al anterior
alembic downgrade -1
```

### Cuándo usar autogenerate vs manual

- **Autogenerate**: cambios simples en modelos (agregar columna, tabla nueva, index).
- **Manual**: operaciones complejas (backfills de datos, renombrar columnas, cambios en constraints).

Para agregar una columna con valor default en datos existentes, la migración manual tiene esta forma:

```python
def upgrade() -> None:
    op.add_column("clusters", sa.Column("topic", sa.String(32), nullable=True))
    # backfill si es necesario:
    op.execute("UPDATE clusters SET topic = 'otros' WHERE topic IS NULL")
```

### pgvector

La migración `0001` activa la extensión:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

Asegurarse de que la imagen de Postgres sea `pgvector/pgvector:pg16`.

---

## Convenciones de código

### Python

- **Type hints** en todas las funciones.
- **async/await** por defecto. Funciones sync solo para utilidades puras (parsing, transformaciones).
- Sin docstrings salvo que la lógica no sea obvia.
- `ruff` para linting (E, F, I, B, UP, ASYNC) con `line-length = 100`.
- `pytest` con `asyncio_mode = "auto"` — no hace falta `@pytest.mark.asyncio` explícito.

```bash
cd api
ruff check src/
ruff format src/
```

### TypeScript / Next.js

- Tipos explícitos en props e interfaces (no `any`).
- `"use client"` solo cuando es necesario (preferir Server Components).
- `export const dynamic = "force-dynamic"` en páginas con datos en tiempo real.
- Clases de Tailwind, sin CSS modules.

---

## Gotchas comunes

### Datetimes timezone-aware en Postgres

Las columnas `TIMESTAMPTZ` de Postgres requieren datetimes con timezone. Usar siempre:

```python
from datetime import UTC, datetime
now = datetime.now(UTC)  # correcto
now = datetime.utcnow()  # deprecated, no usar
```

Sin timezone, SQLAlchemy puede hacer comparaciones incorrectas o lanzar warnings.

### Escape de MarkdownV2 en Telegram

Telegram MarkdownV2 requiere escapar `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`. El proyecto tiene `escape_markdown_v2()` en `notifiers/telegram.py`. Usarlo en **todas** las cadenas interpoladas:

```python
from noticias_api.notifiers.telegram import escape_markdown_v2 as esc
msg = f"Título: {esc(headline)}"
```

### NEXT_PUBLIC_API_URL es build-time

En Next.js, las variables `NEXT_PUBLIC_*` se inlinean en el bundle en tiempo de build, no en runtime. Para cambiarla en producción, hay que reconstruir la imagen o usar el proxy interno (`INTERNAL_API_URL`) para llamadas server-side.

### CORS y proxy routes

Las llamadas POST desde el browser al API FastAPI dan CORS. Usá las route handlers de Next.js (`web/app/api/*`) como proxy para esas llamadas. Ver `web/app/api/qa/route.ts` como ejemplo. El historial de conversación también pasa por un proxy en `web/app/api/qa/history/route.ts`.

### COHERE_API_KEY es opcional en desarrollo

Si no tenés `COHERE_API_KEY` en tu `.env`, el reranking se omite silenciosamente. El sistema usa el top-K del kNN directamente. No lanza excepción ni warning — es un degradado limpio. Acordate de agregar la key si querés testear el comportamiento con reranking real.

### conversation_id en tests de Q&A

Al testear multi-turno, pasá siempre el mismo `conversation_id` entre requests. Sin él, cada llamada crea una conversación nueva y el historial no se carga. Para tests aislados, usá un UUID generado en el fixture para no contaminar otras conversaciones.

### La DB en tests usa pytest-postgresql

`pytest-postgresql` levanta una instancia real de Postgres para cada sesión de test y aplica migraciones automáticamente vía Alembic. Requiere `pg_ctl` en el PATH. En CI o sin Postgres local, usar `docker-compose exec api pytest`.

### Credenciales de GitHub (insteadOf)

El repo usa una regla `url.insteadOf` en la config de git para el credential helper de `gh`. Si clonás el repo en otra máquina y `git push` falla con error de autenticación, asegurate de tener `gh` instalado y autenticado (`gh auth login`) antes de clonar, o configurar el helper manualmente:

```bash
gh auth setup-git
```

---

## Depurar un pipeline fallido

### 1. Ver el run

```bash
curl http://localhost:8000/runs/LAST_ID
# o
curl http://localhost:8000/runs | python -m json.tool | head -60
```

El campo `stats` muestra cuántos artículos pasaron por cada etapa. El campo `error` tiene el traceback si el pipeline tiró una excepción no capturada.

### 2. Logs del contenedor

```bash
docker compose logs api --tail=100
docker compose logs api -f  # follow
```

El logger usa el nivel configurado en `LOG_LEVEL` (default `INFO`). Para debugging, setear `LOG_LEVEL=DEBUG`.

### 3. Chequear artículos sin embedding

```sql
-- Cuántos artículos no tienen embedding todavía
SELECT count(*) FROM articles WHERE embedding IS NULL;
```

### 4. Chequear clusters sin análisis

```sql
SELECT c.id, c.source_count, c.is_top, a.id as analysis_id
FROM clusters c
LEFT JOIN analyses a ON a.cluster_id = c.id
WHERE c.is_top = true AND a.id IS NULL;
```

### 5. Regenerar análisis manualmente

```bash
curl -X POST http://localhost:8000/clusters/101/regenerate-analysis
```

---

## Ver también

- [Arquitectura](architecture.md) — entender el sistema antes de modificarlo
- [API Reference](api-reference.md) — contratos de los endpoints
- [Deployment](deployment.md) — llevar cambios a producción
