# Arquitectura

Descripción técnica del sistema: servicios, modelo de datos, pipeline y algoritmos.

---

## Diagrama de servicios

```
         Diarios argentinos (RSS)
                  │
                  ▼
┌─────────────────────────────────────────────┐
│                  api  (:8000)               │
│                                             │
│  APScheduler ──► pipeline runner            │
│                      │                      │
│                      ▼                      │
│           Postgres 16 + pgvector            │
│           (sources, articles,               │
│            clusters, analyses,              │
│            entities, sagas...)              │
│                      │                      │
│       FastAPI routes ◄─── REST              │
└─────────────────────────────────────────────┘
          │                    │
          │                    │
          ▼                    ▼
   web (:3000)           Telegram Bot API
   Next.js 15            (digest + Q&A)
          │
          ▼
      Browser
```

Los tres servicios corren en Docker Compose:
- `postgres`: `pgvector/pgvector:pg16`, datos persistidos en volumen.
- `api`: FastAPI + Uvicorn, ejecuta el pipeline y expone REST.
- `web`: Next.js en modo standalone, hace proxy de algunas rutas al API para evitar CORS.

OpenAI es el único servicio externo requerido (embeddings + análisis GPT).

---

## Modelo de datos

### Tablas principales

#### `sources`

Las fuentes de noticias (diarios). Sembradas con `seed.py`.

```
id          INTEGER PK
slug        VARCHAR(64) UNIQUE   -- "clarin", "pagina12", etc.
name        VARCHAR(128)         -- "Clarín", "Página 12"
editorial_group VARCHAR(32)      -- "mainstream" | "critico" | "economico"
rss_url     TEXT
base_url    TEXT
enabled     BOOLEAN DEFAULT true
```

#### `articles`

Un artículo por entrada RSS + contenido extraído.

```
id          BIGINT PK
source_id   → sources.id
external_id TEXT                 -- id/guid del RSS
url         TEXT
title       TEXT
summary     TEXT                 -- extracto del RSS
content     TEXT                 -- texto completo extraído (trafilatura)
has_full_text BOOLEAN
published_at TIMESTAMPTZ
fetched_at  TIMESTAMPTZ
embedding   VECTOR(1536)         -- text-embedding-3-large
cluster_id  → clusters.id NULL
tsv         TSVECTOR             -- computed: to_tsvector('spanish', title || content)
```

`(source_id, external_id)` tiene constraint unique para idempotencia.

#### `clusters`

Agrupación de artículos que tratan el mismo hecho.

```
id           BIGINT PK
centroid     VECTOR(1536)         -- media de embeddings de sus artículos
first_seen_at TIMESTAMPTZ
last_seen_at TIMESTAMPTZ
article_count INTEGER
source_count  INTEGER
rank_score    FLOAT               -- score para ordenar el briefing
is_top        BOOLEAN             -- ¿está en el top N del día?
display_date  DATE                -- fecha del briefing donde aparece
topic         VARCHAR(32)         -- "politica" | "economia" | ...
saga_id      → sagas.id NULL
```

#### `analyses`

El análisis generado por GPT-4o para un cluster. Relación 1:1 con clusters.

```
id           BIGINT PK
cluster_id   → clusters.id CASCADE
headline     TEXT
common_facts JSONB                -- list[str]
by_source    JSONB                -- dict[slug, {highlights, framing, tone}]
omissions    JSONB                -- list[{source, not_mentioned}]
divergences  JSONB                -- list[{topic, positions: dict[slug, str]}]
model        VARCHAR(64)          -- "gpt-4o"
prompt_version VARCHAR(16)        -- "v2"
generated_at TIMESTAMPTZ
tsv          TSVECTOR             -- computed: to_tsvector('spanish', headline || common_facts)
```

#### `runs`

Log de ejecuciones del pipeline.

```
id          BIGINT PK
trigger     VARCHAR(16)          -- "cron" | "manual"
status      VARCHAR(16)          -- "running" | "success" | "partial" | "failed"
started_at  TIMESTAMPTZ
finished_at TIMESTAMPTZ NULL
stats       JSONB                -- {fetched, persisted, embedded, clustered, ...}
error       TEXT NULL
```

### Tablas de extensión

#### `sagas`

Agrupación de clusters en historias multi-día.

```
id           BIGINT PK
title        TEXT                 -- headline del cluster más reciente
centroid     VECTOR(1536)         -- media de centroides de clusters miembros
first_seen_at TIMESTAMPTZ
last_seen_at  TIMESTAMPTZ
cluster_count INTEGER
source_count  INTEGER
article_count INTEGER
```

#### `entities`

Entidades nombradas extraídas por GPT-4o-mini.

```
id           BIGINT PK
name         TEXT                 -- forma canónica mostrable
kind         VARCHAR(16)          -- "person" | "org" | "place" | "event"
canonical    TEXT                 -- lowercase sin puntuación (para lookup)
first_seen_at TIMESTAMPTZ
last_seen_at  TIMESTAMPTZ
mention_count INTEGER
```

`(canonical, kind)` tiene constraint unique.

#### `cluster_entities`

M:N entre clusters y entidades.

```
cluster_id  → clusters.id CASCADE (PK)
entity_id   → entities.id CASCADE (PK)
mention_count INTEGER DEFAULT 1
```

#### `cluster_notes`

Anotaciones libres sobre un cluster.

```
id         BIGINT PK
cluster_id → clusters.id CASCADE
note       TEXT
created_at TIMESTAMPTZ
```

#### `deliveries`

Registro de envíos del digest Telegram (idempotencia).

```
id           BIGINT PK
channel      VARCHAR(32)          -- "telegram"
chat_id      VARCHAR(64)
display_date DATE
message_hash VARCHAR(64)          -- SHA del contenido del mensaje
sent_at      TIMESTAMPTZ
status       VARCHAR(16)          -- "sent" | "error"
error        TEXT NULL
```

Unique constraint `(channel, chat_id, display_date, message_hash)`.

#### `subscriptions`

Suscripciones al digest/alertas.

```
id                   BIGINT PK
channel              VARCHAR(32)
chat_id              VARCHAR(64)
kind                 VARCHAR(16)   -- "entity" | "topic" | "all"
value                TEXT NULL     -- entidad o topic a filtrar
alert_threshold_sources INTEGER NULL
created_at           TIMESTAMPTZ
```

#### `qa_messages`

Historial de conversaciones de Q&A (web y bot Telegram).

```
id              BIGINT PK
conversation_id VARCHAR(64)          -- UUID para web, "telegram:{chat_id}" para bot
role            VARCHAR(16)          -- "user" | "assistant"
content         TEXT                 -- texto del mensaje
citations       JSONB NULL           -- solo en rol "assistant": lista de citas usadas
used_citations  JSONB NULL           -- índices de citas referenciadas en el texto
hyde_query      TEXT NULL            -- texto hipotético generado por HyDE (solo assistant)
model           VARCHAR(64)          -- modelo usado (ej: "gpt-4o")
created_at      TIMESTAMPTZ
```

Índice sobre `(conversation_id, created_at)` para recuperar el historial cronológico de una conversación en tiempo O(log n).

#### `alert_deliveries`

Registro de alertas enviadas (evita duplicados).

```
id              BIGINT PK
channel         VARCHAR(32)
chat_id         VARCHAR(64)
cluster_id      → clusters.id CASCADE
subscription_id → subscriptions.id CASCADE NULL
sent_at         TIMESTAMPTZ
status          VARCHAR(16)
error           TEXT NULL
```

Unique constraint `(channel, chat_id, cluster_id, subscription_id)`.

---

## Pipeline

El pipeline corre secuencialmente en un solo proceso. Se dispara por:

- **Cron**: APScheduler, configurable con `CRON_HOUR` / `CRON_HOURS`.
- **Manual**: POST `/refresh` desde el frontend o el admin.

### Etapas

```
1. fetch_feed     ──► Parse RSS de cada fuente habilitada
2. persist_items  ──► Upsert artículos (idempotente por external_id)
3. extract_content──► Trafilatura: obtener texto completo de cada URL
4. embed_texts    ──► Embeddings con text-embedding-3-large (batch)
5. cluster        ──► kNN greedy: asignar cluster a cada artículo
6. merge_clusters ──► Segunda pasada: fusionar clusters similares
7. assign_sagas   ──► Tercera pasada: agrupar clusters en sagas (7d)
8. rank_top       ──► Calcular rank_score y marcar top N
9. analyze        ──► GPT-4o: generar análisis por cluster top
10. extract_entities──► GPT-4o-mini: extraer entidades nombradas
11. classify_topic ──► GPT-4o-mini: clasificar tema del cluster
```

#### 1-2. Fetch + Persist

`fetch_feed` hace HTTP GET al RSS con hasta 2 reintentos. `parse_feed` filtra entradas anteriores a la ventana de `window_hours`. `persist_items` inserta o ignora por `(source_id, external_id)`.

**Stats:** `fetched` (items del RSS), `persisted` (insertados nuevos).

#### 3. Extract content

`extract_content` usa `trafilatura` para extraer texto completo del HTML. Si falla o no hay texto, el artículo queda con `has_full_text=False` y se usa el `summary` del RSS como fallback.

**Stats:** `extracted` (artículos actualizados con contenido).

#### 4. Embed

`embed_texts` llama a `client.embeddings.create` con `model=text-embedding-3-large, dimensions=1536`. Se procesa en batch (hasta 500 artículos por corrida). El input es `title + "\n\n" + content[:2000]`.

**Por qué `text-embedding-3-large`:** ofrece mejor calidad semántica que `text-embedding-3-small` a dimensionalidad equivalente (1536), lo que mejora la precisión del clustering. El parámetro `dimensions=1536` trunca la salida nativa de 3072 dimensiones para que quepa en el esquema pgvector existente.

**Stats:** `embedded`.

#### 5. Cluster (greedy kNN)

Para cada artículo sin cluster en la ventana de `window_hours`:

1. Busca el artículo más cercano **que ya tiene cluster** usando `cosine_distance` sobre pgvector.
2. Si `similarity >= threshold` (default 0.70): se une a ese cluster.
3. Si no: crea un cluster nuevo con ese artículo como semilla.

El orden de procesamiento es cronológico (`published_at`). Al final se recomputan `article_count`, `source_count` y `last_seen_at` para los clusters afectados.

**Stats:** `clustered`, `new_clusters`.

#### 6. Merge (segunda pasada)

Después del clustering greedy, puede haber clusters "hermanos" con centroides muy similares que no se unieron porque se formaron antes de que los artículos del otro llegaran.

1. Recomputa los centroides como media de los embeddings actuales.
2. Construye una matriz de similitudes coseno entre todos los clusters en la ventana.
3. Union-Find: si `cosine_sim(i,j) >= merge_threshold` (default 0.85), los fusiona.
4. El cluster con id menor es el canónico. Los artículos del absorbido se reasignan; el cluster absorbido se elimina (y su análisis en cascade).

**Stats:** `merged_clusters`.

#### 7. Sagas

Opera sobre la ventana de `saga_window_hours` (default 168h = 7 días).

1. Pull de clusters con centroide no nulo en la ventana.
2. Misma lógica Union-Find que el merge, pero con `saga_threshold` (default 0.78).
3. Los grupos de ≥2 clusters se convierten en sagas (o se unen a sagas existentes).
4. Los singletons se des-asocian de su saga.
5. El título de la saga es el headline del cluster más reciente del grupo.

**Stats:** `sagas_clusters_assigned`, `sagas_active`.

#### 8. Rank

```python
score = source_count * 2 + log(article_count + 1) - hours_ago * 0.05
```

Solo clusters con `source_count >= 2` son candidatos. Los top N clusters reciben `is_top=True` y `display_date=today`.

#### 9. Analyze (GPT-4o)

Para cada cluster `is_top` sin análisis actualizado:

- Input: `[{slug, title, body[:3000]}]` por cada artículo del cluster.
- Prompt: ver [prompts.py](../api/src/noticias_api/pipeline/prompts.py) — `PROMPT_VERSION = "v2"`.
- Output esperado: JSON con `headline`, `common_facts`, `by_source`, `omissions`, `divergences`.
- `response_format={"type": "json_object"}`, dos reintentos con temperatura `[0.3, 0.0]`.

Si el análisis existente es más reciente que `last_seen_at` del cluster, se omite (idempotente).

**Costo aproximado:** ~3K-8K tokens de entrada por cluster, ~1K-2K de salida. Con GPT-4o a precios actuales, un briefing de 20 clusters cuesta ~$0.20-0.50 USD.

#### 10. Entity extraction (GPT-4o-mini)

Para cada cluster `is_top` con análisis y sin entidades ya asignadas:

- Input: `headline + common_facts`.
- Extrae `persons`, `orgs`, `places`, `events`.
- Canonicaliza: lowercase, sin puntuación, sin espacios múltiples.
- Upsert en `entities` + insert en `cluster_entities`.
- Idempotente: si el cluster ya tiene `cluster_entities`, se salta.

#### 11. Topic classification (GPT-4o-mini)

Para cada cluster `is_top` con análisis pero sin `topic`:

- Input: `headline + common_facts[:2000]`.
- Output: uno de `politica | economia | deportes | internacional | sociedad | espectaculos | otros`.
- `response_format={"type": "json_object"}`, temperatura 0.0.
- Idempotente: si `cluster.topic` ya está seteado, se salta.

---

## Clustering: detalles del algoritmo

### Por qué greedy kNN en vez de DBSCAN o k-means

El corpus crece continuamente y los artículos llegan en orden temporal. El greedy kNN es:

- **Online**: procesa artículos según llegan sin requerir todos los datos por adelantado.
- **Eficiente**: una sola query de vecino más cercano por artículo, aprovechando el índice pgvector.
- **Determinístico**: el orden `published_at` hace reproducibles los resultados dado el mismo input.

El merge pass corrige los casos donde clusters "hermanos" se forman en paralelo antes de cruzarse.

### Thresholds

| Threshold | Default | Efecto si sube | Efecto si baja |
|-----------|---------|----------------|----------------|
| `SIMILARITY_THRESHOLD` | 0.70 | Clusters más cohesivos, más clusters en total | Clusters más grandes, posible mezcla de temas |
| `MERGE_THRESHOLD` | 0.85 | Menos fusiones en la segunda pasada | Más fusiones agresivas |
| `SAGA_THRESHOLD` | 0.78 | Sagas más estrictas | Sagas más amplias |

---

## RAG pipeline (Q&A)

### Pipeline completo

```
query (texto)
    │
    ▼ HyDE — gpt-4o-mini
genera "respuesta hipotética" con estilo periodístico
    │
    ▼ embed (text-embedding-3-large, 1536d)
embedding del texto hipotético (no de la query original)
    │
    ▼ kNN — pgvector
SELECT articles ORDER BY embedding <=> hyde_vec LIMIT 50
    │
    ▼ Cohere v2/rerank (rerank-multilingual-v3.0)
re-rankea los 50 candidatos → top 10
(se omite si COHERE_API_KEY no está configurado; pasa directamente los primeros 10 del kNN)
    │
    ▼ CRAG-lite — gpt-4o-mini
evalúa la relevancia de cada chunk individualmente:
  ├── ≥3 relevantes → "confident": descarta irrelevantes
  ├── 1-2 relevantes → "partial": conserva todos + activa prompt de advertencia
  └── 0 relevantes → "empty": retorna "No encontré información..." sin llamar a GPT-4o
    │
    ▼ cargar historial de conversación
últimos N turnos de qa_messages (conversation_id, rol, contenido)
    │
    ▼ síntesis — gpt-4o
prompt consciente de confianza: con/sin advertencia de cobertura parcial
instrucción de citar solo con [N] inline, no inventar datos
    │
    ▼ persistencia
INSERT en qa_messages: mensaje del usuario + respuesta del asistente
    │
    ▼
QAResponse {
  answer, citations, used_citations,
  conversation_id, hyde_query, confidence, crag_verdicts
}
```

### Por qué HyDE

Un embedding de la pregunta original (`¿Qué dijo La Nación sobre el FMI?`) está en el espacio semántico de las preguntas, que es diferente al espacio de los artículos periodísticos. HyDE genera primero una "respuesta hipotética" con lenguaje similar al corpus (afirmaciones declarativas, estilo nota), la embeddea, y usa ese vector para recuperar artículos. Esto mejora el recall, especialmente en queries vagas o cortas.

El texto hipotético se incluye en `hyde_query` en la respuesta para transparencia.

### Por qué Cohere rerank

El primer paso de recuperación usa un bi-encoder (text-embedding-3-large): rápido y escalable pero compara vectores aislados. El reranker de Cohere es un cross-encoder: ve query y documento juntos en el mismo contexto, lo que le permite capturar matices como filtros por fuente específica (`¿qué dijo Clarín?`) que el bi-encoder pierde.

Si `COHERE_API_KEY` no está configurado, el sistema degrada graciosamente: omite el paso y usa el top-K directo del kNN.

### Por qué CRAG-lite

El pipeline RAG clásico siempre pasa los fragmentos al LLM y deja que este "admita" que no sabe. El problema: GPT-4o tiende a sintetizar algo incluso con material irrelevante. CRAG-lite fuerza una verificación de relevancia por chunk antes de la síntesis:

- **confident** (≥3 chunks relevantes): respuesta normal.
- **partial** (1-2 relevantes): respuesta con advertencia de cobertura limitada.
- **empty** (0 relevantes): corto-circuita sin llamar a GPT-4o, retorna mensaje de "no encontré información".

El campo `crag_verdicts` en la respuesta expone los dictámenes por chunk (`{"1": "relevant", "2": "not_relevant", ...}`).

### Memoria de conversación

Cada sesión de Q&A tiene un `conversation_id`:

- **Web**: UUID generado en el primer mensaje, persistido en `localStorage` bajo la clave `noticias:qa-conversation`. El botón "Nueva conversación" limpia el key.
- **Bot Telegram**: `f"telegram:{chat_id}"` — cada chat tiene memoria propia automáticamente.

Los últimos `qa_history_turns` turnos (default 6) se cargan de `qa_messages` y se insertan en el prompt antes de la síntesis. Esto permite preguntas de seguimiento (`¿y qué dijo Página 12?`) sin repetir el contexto.

---

---

## Telegram: digest y bot

### Digest

`send_digest(session, settings, date, force=False)`:

1. Carga clusters `is_top` con `display_date == date`.
2. Construye un mensaje MarkdownV2 con headline, fuentes y link a la web.
3. Calcula SHA256 del mensaje como `message_hash`.
4. Chequea en `deliveries` si ya existe `(channel, chat_id, date, message_hash)`. Si existe y `force=False`, no envía.
5. Envía con `bot.send_message(chat_id, text)`.
6. Registra en `deliveries`.

**Alertas:** `send_alerts` corre después de cada pipeline. Para cada suscripción activa busca clusters nuevos que crucen el `alert_threshold_sources` y no estén en `alert_deliveries`. Envía una alerta por cluster nuevo.

### Bot (bot_handler.py)

El bot usa el mismo pipeline de Q&A que el endpoint `/qa`. Soporta:

- `/start` → mensaje de bienvenida.
- `/help` → lista de comandos.
- Texto libre → RAG sobre el corpus con respuesta en MarkdownV2.

**Memoria conversacional:** el bot pasa `conversation_id = f"telegram:{chat_id}"` en cada llamada a `/qa`. Cada chat Telegram tiene así su propia memoria de los últimos 6 turnos (configurable con `qa_history_turns`) sin ninguna configuración extra.

Para chats no autorizados (definidos por `TELEGRAM_ALLOWED_CHATS`), el bot ignora silenciosamente los mensajes.

**Escape MarkdownV2:** Telegram v2 requiere escapar caracteres especiales. El cliente usa `escape_markdown_v2()` en todas las cadenas interpoladas.

### Webhook vs polling

| Modo | Cuándo usar |
|------|-------------|
| `webhook` | Producción con URL pública (ver deployment.md) |
| `polling` | Desarrollo local sin URL pública |

El poller usa long-polling (`getUpdates`) y corre en un thread separado iniciado en `lifespan`.

---

## Prompt versioning

| Versión | Cambios |
|---------|---------|
| `v1` | Prompt inicial: estructura básica headline/common_facts/by_source/omissions/divergences |
| `v2` | Prompt actual: más detalle en highlights (5-7 puntos, 1-2 oraciones c/u), framing más concreto, regla explícita contra generalidades vagas, indicación para cobertura escueta |

El `prompt_version` se almacena en cada `Analysis`. Al comparar análisis generados con versiones distintas, el campo ayuda a entender diferencias de estilo.

---

## Caching e idempotencia

| Mecanismo | Qué protege |
|-----------|-------------|
| `UNIQUE(source_id, external_id)` en articles | No insertar el mismo artículo dos veces |
| Skip si `analysis.generated_at >= cluster.last_seen_at` | No re-analizar clusters sin cambios |
| Skip si `cluster_entities` ya tiene filas | No re-extraer entidades |
| Skip si `cluster.topic != NULL` | No re-clasificar tema |
| `UNIQUE(channel, chat_id, display_date, message_hash)` en deliveries | No reenviar el mismo digest |
| `UNIQUE(channel, chat_id, cluster_id, subscription_id)` en alert_deliveries | No reenviar la misma alerta |

---

## Ver también

- [API Reference](api-reference.md)
- [Development](development.md)
- [Deployment](deployment.md)
