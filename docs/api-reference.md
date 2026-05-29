# API Reference

Base URL: `http://localhost:8000` en desarrollo. En producción, el frontend hace proxy de algunas rutas via Next.js route handlers en `/api/*`.

Todos los endpoints son abiertos (sin autenticación) en esta versión.

---

## Health & meta

### `GET /healthz`

Chequeo de salud del servicio.

**Response:**
```json
{"status": "ok"}
```

---

## Sources

### `GET /sources`

Lista todas las fuentes configuradas.

**Response:** `SourceOut[]`
```json
[
  {
    "slug": "clarin",
    "name": "Clarín",
    "editorial_group": "mainstream",
    "rss_url": "https://www.clarin.com/rss/lo-ultimo/",
    "base_url": "https://www.clarin.com",
    "enabled": true
  }
]
```

### `PATCH /sources/{slug}`

Habilitar o deshabilitar una fuente.

**Path param:** `slug` — slug de la fuente (ej: `clarin`)

**Body:**
```json
{"enabled": false}
```

**Response:** `SourceOut` actualizado.

**Errors:** `404` si el slug no existe.

---

## Pipeline

### `POST /refresh`

Dispara el pipeline manualmente en background. Si el pipeline ya está corriendo, retorna `409`.

**Response:** `202 Accepted`
```json
{"run_id": 0, "status": "queued"}
```

Nota: `run_id=0` es un placeholder — el ID real se genera async. Usá `GET /runs/current` para obtener el run activo.

**Errors:** `409` si ya hay un pipeline corriendo:
```json
{"detail": {"run_id": 42, "status": "running"}}
```

### `GET /runs/current`

Retorna el run actualmente en ejecución, o `null` si no hay ninguno.

**Response:** `RunOut | null`
```json
{
  "id": 42,
  "trigger": "manual",
  "status": "running",
  "started_at": "2026-05-09T07:00:00Z",
  "finished_at": null,
  "stats": null,
  "error": null
}
```

### `GET /runs/{run_id}`

Detalle de un run específico.

**Path param:** `run_id`

**Response:** `RunOut`
```json
{
  "id": 42,
  "trigger": "cron",
  "status": "success",
  "started_at": "2026-05-09T07:00:00Z",
  "finished_at": "2026-05-09T07:08:30Z",
  "stats": {
    "fetched": 312,
    "persisted": 47,
    "extracted": 47,
    "embedded": 47,
    "clustered": 38,
    "new_clusters": 12,
    "merged_clusters": 2,
    "analyzed": 20,
    "sagas_clusters_assigned": 8,
    "sagas_active": 3,
    "entities_extracted": 18,
    "topics_classified": 15,
    "errors_per_source": {}
  },
  "error": null
}
```

**Status values:** `running` | `success` | `partial` | `failed`

**Errors:** `404` si no existe.

### `GET /runs`

Lista los últimos N runs.

**Query params:**
- `limit` (int, default 20): máximo de resultados.

**Response:** `RunOut[]` ordenados por id descendente.

---

## Briefings

### `GET /briefings/today`

Briefing del día actual.

**Query params:**
- `topic` (str, opcional): filtrar por tema (`politica`, `economia`, `deportes`, `internacional`, `sociedad`, `espectaculos`, `otros`).

**Response:** `BriefingOut`
```json
{
  "date": "2026-05-09",
  "generated_at": "2026-05-09T07:08:30Z",
  "clusters": [
    {
      "id": 101,
      "headline": "Milei cierra acuerdo con el FMI por USD 20 mil millones",
      "source_count": 6,
      "article_count": 9,
      "sources": ["clarin", "lanacion", "infobae", "pagina12", "ambito", "cronista"],
      "rank_score": 14.2,
      "common_facts": ["El acuerdo fue firmado el lunes", "El monto es USD 20.000 millones"],
      "divergence_count": 3,
      "topic": "politica"
    }
  ]
}
```

### `GET /briefings/{target_date}`

Briefing de una fecha específica.

**Path param:** `target_date` — fecha en formato `YYYY-MM-DD`.

**Query params:** igual que `/briefings/today`.

**Response:** `BriefingOut`

### `GET /briefings`

Lista de fechas con briefing disponible.

**Response:** `date[]` (ISO strings) ordenadas descendente.
```json
["2026-05-09", "2026-05-08", "2026-05-07"]
```

---

## Clusters

### `GET /clusters/{cluster_id}`

Detalle completo de un cluster incluyendo análisis, artículos, entidades y saga.

**Path param:** `cluster_id`

**Response:** `ClusterDetail`
```json
{
  "id": 101,
  "first_seen_at": "2026-05-09T06:00:00Z",
  "last_seen_at": "2026-05-09T07:30:00Z",
  "article_count": 9,
  "source_count": 6,
  "topic": "politica",
  "saga": {"id": 5, "title": "Negociación con el FMI"},
  "entities": [
    {"id": 12, "name": "Javier Milei", "kind": "person"},
    {"id": 7, "name": "FMI", "kind": "org"}
  ],
  "analysis": {
    "headline": "Milei cierra acuerdo con el FMI por USD 20 mil millones",
    "common_facts": ["El acuerdo fue firmado el lunes 8 de mayo"],
    "by_source": {
      "clarin": {
        "highlights": ["Milei anunció el acuerdo en cadena nacional"],
        "framing": "Clarín enmarca el acuerdo como un logro del gobierno...",
        "tone": "favorable"
      }
    },
    "omissions": [
      {"source": "lanacion", "not_mentioned": "El impacto en jubilaciones"}
    ],
    "divergences": [
      {
        "topic": "Monto real del acuerdo",
        "positions": {
          "clarin": "USD 20.000 millones confirmados",
          "pagina12": "La cifra real sería menor según fuentes del FMI"
        }
      }
    ],
    "model": "gpt-4o",
    "prompt_version": "v2",
    "generated_at": "2026-05-09T07:08:00Z"
  },
  "articles": [
    {
      "id": 500,
      "source": {"slug": "clarin", "name": "Clarín", "editorial_group": "mainstream"},
      "title": "Milei anunció el acuerdo con el FMI",
      "url": "https://www.clarin.com/...",
      "summary": "El presidente anunció...",
      "has_full_text": true,
      "published_at": "2026-05-09T06:00:00Z"
    }
  ]
}
```

**Errors:** `404` si no existe.

### `POST /clusters/{cluster_id}/regenerate-analysis`

Borra el análisis existente y lo regenera llamando a GPT-4o.

**Path param:** `cluster_id`

**Response:** `AnalysisOut` (mismo objeto que `analysis` dentro de `ClusterDetail`).

**Errors:**
- `404` si el cluster no existe.
- `400` si el cluster no tiene artículos.
- `502` si la regeneración falla.

---

## Notes

### `GET /clusters/{cluster_id}/notes`

Lista las notas de un cluster, ordenadas por fecha descendente.

**Path param:** `cluster_id`

**Response:** `NoteOut[]`
```json
[
  {
    "id": 3,
    "cluster_id": 101,
    "note": "Revisar la cobertura de mañana",
    "created_at": "2026-05-09T10:00:00Z"
  }
]
```

**Errors:** `404` si el cluster no existe.

### `POST /clusters/{cluster_id}/notes`

Agrega una nota a un cluster.

**Path param:** `cluster_id`

**Body:**
```json
{"note": "Revisar la cobertura de mañana"}
```

`note` debe tener entre 1 y 2000 caracteres.

**Response:** `201 Created`, `NoteOut`

**Errors:** `404` si el cluster no existe.

### `DELETE /notes/{note_id}`

Elimina una nota.

**Path param:** `note_id`

**Response:** `204 No Content`

**Errors:** `404` si la nota no existe.

---

## Sagas

### `GET /sagas`

Lista las sagas ordenadas por `last_seen_at` descendente.

**Query params:**
- `limit` (int, default 30)

**Response:** `SagaSummary[]`
```json
[
  {
    "id": 5,
    "title": "Negociación con el FMI",
    "cluster_count": 4,
    "source_count": 7,
    "article_count": 28,
    "first_seen_at": "2026-05-01T00:00:00Z",
    "last_seen_at": "2026-05-09T07:30:00Z"
  }
]
```

### `GET /sagas/{saga_id}`

Detalle de una saga con todos sus clusters.

**Path param:** `saga_id`

**Response:** `SagaDetail`
```json
{
  "id": 5,
  "title": "Negociación con el FMI",
  "cluster_count": 4,
  "source_count": 7,
  "article_count": 28,
  "first_seen_at": "2026-05-01T00:00:00Z",
  "last_seen_at": "2026-05-09T07:30:00Z",
  "clusters": [
    {
      "id": 101,
      "headline": "Milei cierra acuerdo con el FMI",
      "source_count": 6,
      "article_count": 9,
      "last_seen_at": "2026-05-09T07:30:00Z",
      "is_top": true
    }
  ]
}
```

**Errors:** `404` si no existe.

---

## Entities

### `GET /entities`

Lista de entidades ordenadas por cluster_count descendente.

**Query params:**
- `kind` (str, opcional): filtrar por tipo (`person` | `org` | `place` | `event`).
- `q` (str, opcional, min 2, max 100): búsqueda parcial sobre `canonical` (ilike).
- `limit` (int, default 50, max 200)

**Response:** `EntitySummary[]`
```json
[
  {
    "id": 12,
    "name": "Javier Milei",
    "kind": "person",
    "canonical": "javier milei",
    "mention_count": 47,
    "cluster_count": 23,
    "last_seen_at": "2026-05-09T07:00:00Z"
  }
]
```

### `GET /entities/{entity_id}`

Detalle de una entidad con sus clusters (últimos 50).

**Path param:** `entity_id`

**Response:** `EntityDetail`
```json
{
  "id": 12,
  "name": "Javier Milei",
  "kind": "person",
  "canonical": "javier milei",
  "mention_count": 47,
  "cluster_count": 23,
  "last_seen_at": "2026-05-09T07:00:00Z",
  "clusters": [
    {
      "id": 101,
      "headline": "Milei cierra acuerdo con el FMI",
      "source_count": 6,
      "article_count": 9,
      "last_seen_at": "2026-05-09T07:30:00Z",
      "is_top": true
    }
  ]
}
```

**Errors:** `404` si no existe.

---

## Search

### `GET /search`

Búsqueda de texto completo sobre artículos y análisis (Postgres FTS, diccionario español).

**Query params:**
- `q` (str, min 2, max 200): query de búsqueda. **Requerido.**
- `limit` (int, default 30)

**Response:** `SearchResults`
```json
{
  "query": "acuerdo FMI",
  "clusters": [
    {
      "id": 101,
      "headline": "Milei cierra acuerdo con el FMI",
      "source_count": 6,
      "article_count": 9,
      "rank": 0.82
    }
  ],
  "articles": [
    {
      "id": 500,
      "title": "Milei anunció el acuerdo con el FMI",
      "url": "https://www.clarin.com/...",
      "source_slug": "clarin",
      "cluster_id": 101,
      "published_at": "2026-05-09T06:00:00Z",
      "rank": 0.75
    }
  ]
}
```

---

## Q&A

### `POST /qa`

Pregunta al corpus usando el pipeline RAG completo: HyDE → kNN → reranking → CRAG-lite → síntesis con GPT-4o. Mantiene memoria de conversación por `conversation_id`.

**Body:**
```json
{
  "query": "¿Qué dijo La Nación sobre el acuerdo con el FMI?",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

- `query`: requerido, 3-500 caracteres.
- `conversation_id`: opcional. Si se omite, se genera uno nuevo y se retorna en la respuesta. Pasarlo en llamadas sucesivas para mantener contexto de conversación.

**Response:** `QAResponse`
```json
{
  "query": "¿Qué dijo La Nación sobre el acuerdo con el FMI?",
  "answer": "La Nación destacó que el acuerdo fue firmado el lunes [1] y que el monto es de USD 20.000 millones [2].",
  "used_citations": [1, 2],
  "citations": [
    {
      "n": 1,
      "article_id": 501,
      "cluster_id": 101,
      "source_slug": "lanacion",
      "source_name": "La Nación",
      "title": "El gobierno llegó a un acuerdo con el FMI",
      "url": "https://www.lanacion.com.ar/...",
      "published_at": "2026-05-09T06:30:00Z",
      "snippet": "El presidente Milei anunció el lunes..."
    }
  ],
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "hyde_query": "La Nación informó que el acuerdo con el FMI fue firmado el lunes por el presidente Milei...",
  "confidence": "confident",
  "crag_verdicts": {
    "1": "relevant",
    "2": "relevant",
    "3": "not_relevant",
    "4": "ambiguous"
  }
}
```

**Campos nuevos en la respuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `conversation_id` | `str` | ID de la conversación. Usar en la siguiente request para continuar el hilo. |
| `hyde_query` | `str \| null` | Texto hipotético generado por HyDE (para debugging/transparencia). `null` si HyDE está desactivado. |
| `confidence` | `"confident" \| "partial" \| "empty"` | Veredicto de CRAG-lite. `empty` indica que no se encontró información relevante. |
| `crag_verdicts` | `dict[str, str] \| null` | Veredictos por chunk (`"relevant"`, `"ambiguous"`, `"not_relevant"`). `null` si CRAG está desactivado. |

**Comportamiento por nivel de confianza:**

| `confidence` | Qué pasó | Qué retorna |
|-------------|----------|-------------|
| `confident` | ≥3 chunks relevantes | Respuesta normal con citas. |
| `partial` | 1-2 chunks relevantes | Respuesta con advertencia de cobertura limitada. |
| `empty` | 0 chunks relevantes | `answer` es un mensaje de "no encontré información". No se llama a GPT-4o. |

**Errors:** `500` si `OPENAI_API_KEY` no está configurado.

---

### `GET /qa/history`

Retorna el historial de mensajes de una conversación en orden cronológico.

**Query params:**
- `conversation_id` (str, requerido): ID de la conversación.
- `limit` (int, default 20): máximo de mensajes a retornar.

**Response:** `QAMessage[]`
```json
[
  {
    "id": 1,
    "role": "user",
    "content": "¿Qué dijo La Nación sobre el acuerdo con el FMI?",
    "citations": null,
    "used_citations": null,
    "created_at": "2026-05-09T10:00:00Z"
  },
  {
    "id": 2,
    "role": "assistant",
    "content": "La Nación destacó que el acuerdo fue firmado el lunes [1]...",
    "citations": [
      {
        "n": 1,
        "article_id": 501,
        "source_slug": "lanacion",
        "title": "El gobierno llegó a un acuerdo con el FMI",
        "url": "https://www.lanacion.com.ar/..."
      }
    ],
    "used_citations": [1],
    "created_at": "2026-05-09T10:00:05Z"
  }
]
```

**Errors:** `422` si falta `conversation_id`.

---

## Authors

### `GET /authors`

Lista autores ordenados por actividad.

**Query params:**
- `source` (str, opcional): filtrar por slug de fuente (ej: `clarin`).
- `q` (str, opcional): búsqueda parcial sobre el nombre del autor.
- `order` (`articles_desc` | `last_seen_desc` | `name_asc`, default `articles_desc`): ordenamiento.
- `limit` (int, default 50): máximo de resultados.

**Response:** `{authors: AuthorSummary[]}`

---

### `GET /authors/{slug}/stats`

Actividad del autor: totales, distribución por tópico, historial mensual y entidades más mencionadas.

**Path param:** `slug` — slug del autor.

**Response:** `AuthorStats`
```json
{
  "author": {"slug": "juan-perez", "name": "Juan Pérez", "source": "clarin", "is_synthetic": false},
  "totals": {"article_count": 47, "cluster_count": 23},
  "by_topic": {"politica": 20, "economia": 15, "otros": 12},
  "by_month": [{"month": "2026-04", "article_count": 12}],
  "top_entities": [{"name": "Javier Milei", "kind": "person", "mention_count": 8}]
}
```

**Errors:** `404` si el slug no existe.

---

### `GET /authors/{slug}/scorecard`

Métricas de sesgo del autor con comparativa respecto al baseline de su diario.

**Path param:** `slug`

**Response:** `AuthorScorecard`
```json
{
  "article_count": 47,
  "sufficient_sample": true,
  "tone": {"neutral": 0.45, "critico": 0.30, "favorable": 0.25},
  "omission_rate": 0.18,
  "divergence_score": 2.3,
  "framing_diversity": 0.61,
  "vs_source_baseline": {
    "omission_rate_delta": 0.04,
    "divergence_score_delta": -0.5
  }
}
```

`sufficient_sample: false` cuando el autor tiene menos de 3 artículos.

**Errors:** `404` si el slug no existe.

---

### `GET /authors/{slug}/articles`

Lista de artículos del autor, ordenados por fecha descendente.

**Path param:** `slug`

**Query params:**
- `limit` (int, default 20): máximo de resultados.

**Response:** `ArticleSummary[]`

**Errors:** `404` si el slug no existe.

---

### `GET /authors/{slug}/profile`

Perfil cualitativo generado por LLM. Retorna `404` si aún no fue generado.

**Path param:** `slug`

**Response:** `AuthorProfile`
```json
{
  "summary": "Juan Pérez tiende a encuadrar la política económica...",
  "strengths": ["Precisión factual en notas de economía"],
  "patterns": ["Tono favorable al gobierno en temas fiscales"],
  "model": "gpt-4o",
  "generated_at": "2026-05-09T10:00:00Z"
}
```

**Errors:** `404` si el slug no existe o el perfil no fue generado.

---

### `POST /authors/{slug}/profile/regenerate`

Genera o regenera el perfil cualitativo del autor usando GPT-4o.

**Path param:** `slug`

**Response:** `AuthorProfile` (igual que `GET /authors/{slug}/profile`).

**Errors:**
- `404` si el slug no existe.
- `400` si el autor tiene menos de 3 artículos.

---

### `GET /authors/{slug}/similar`

Autores con perfil parecido, combinando similitud de centroide (embeddings) y profile_vector (distribución estadística).

**Path param:** `slug`

**Query params:**
- `weight_topic` (float, default 0.5): peso del profile_vector en la similitud combinada.
- `weight_profile` (float, default 0.5): peso del centroide de embeddings.
- `limit` (int, default 10): máximo de resultados.

**Response:** `{similar: [{author: AuthorSummary, score: float}]}`

**Errors:** `404` si el slug no existe.

---

### `POST /authors/compare`

Comparación LLM entre dos autores. Cacheada por `(a_id, b_id, since, until)`. Si no hay clusters en común (`overlap_clusters=0`), retorna un fast-path sin llamar al LLM.

**Body:**
```json
{
  "a": "juan-perez",
  "b": "maria-garcia",
  "since": "2026-04-01",
  "until": "2026-05-01"
}
```

`since` y `until` son opcionales (default: últimos 30 días).

**Response:** `AuthorComparison`
```json
{
  "overlap_clusters": 8,
  "comparison": "Juan Pérez y María García coinciden en cobertura de política exterior pero divergen...",
  "cached": false,
  "model": "gpt-4o",
  "generated_at": "2026-05-09T11:00:00Z"
}
```

---

### `GET /authors/compare/clusters`

Lista de clusters que tienen artículos de ambos autores.

**Query params:**
- `a` (str, requerido): slug del primer autor.
- `b` (str, requerido): slug del segundo autor.

**Response:** `{clusters: ClusterSummary[]}`

---

### `GET /clusters/{id}/by-author`

Artículos de dos autores en un cluster específico. Útil para mostrar la comparación lado a lado en el detalle de un cluster.

**Path param:** `id` — cluster id.

**Query params:**
- `a` (str, requerido): slug del primer autor.
- `b` (str, requerido): slug del segundo autor.

**Response:** `{a: ArticleSummary[], b: ArticleSummary[]}`

**Errors:** `404` si el cluster no existe.

---

### `GET /sources/{slug}/byline-coverage`

Porcentaje de notas con firma real vs sintética (`"Redacción <Diario>"`), agrupado por mes.

**Path param:** `slug` — slug de la fuente.

**Response:** `{months: [{month: str, real: int, synthetic: int, pct_real: float}]}`

**Errors:** `404` si la fuente no existe.

---

## Analytics

### `GET /analytics/tone-trends`

Distribución de tonos por diario a lo largo del tiempo.

**Query params:**
- `entity` (str, opcional, min 2, max 80): filtrar por entidad canónica (ej: `javier milei`).
- `since` (date, opcional): fecha de inicio. Default: últimos 30 días.
- `until` (date, opcional): fecha de fin. Default: ahora.
- `bucket` (`week` | `day`, default `week`): granularidad de los buckets temporales.

**Response:** `ToneTrends`
```json
{
  "buckets": ["2026-04-20", "2026-04-27", "2026-05-04"],
  "sources": ["ambito", "clarin", "lanacion"],
  "tones": ["favorable", "celebratorio", "neutral", "critico", "esceptico", "alarmista", "otro"],
  "data": {
    "clarin": {
      "2026-05-04": {"neutral": 3, "favorable": 2, "critico": 1}
    }
  }
}
```

### `GET /analytics/bias-scorecard`

Tabla cruzada fuente × entidad con distribución de tonos.

**Query params:**
- `since` (date, opcional): fecha de inicio. Default: últimos 30 días.
- `top_entities` (int, default 8, min 2, max 20): cuántas entidades mostrar.
- `kind` (`person` | `org` | `place` | `event`, default `person`): tipo de entidad.

**Response:** `BiasScorecard`
```json
{
  "entities": [
    {"canonical": "javier milei", "name": "Javier Milei", "cluster_count": 23}
  ],
  "rows": [
    {
      "source": "clarin",
      "cells": {
        "javier milei": {
          "favorable": 5,
          "critico": 2,
          "neutral": 8,
          "other": 1,
          "total": 16
        }
      }
    }
  ]
}
```

---

## Subscriptions

### `GET /subscriptions`

Lista las suscripciones activas para el `TELEGRAM_CHAT_ID` configurado.

**Response:** `SubscriptionOut[]`
```json
[
  {
    "id": 1,
    "channel": "telegram",
    "chat_id": "123456789",
    "kind": "entity",
    "value": "javier milei",
    "alert_threshold_sources": 4,
    "created_at": "2026-05-08T10:00:00Z"
  }
]
```

**Errors:** `400` si `TELEGRAM_CHAT_ID` no está configurado.

### `POST /subscriptions`

Crea una nueva suscripción.

**Body:**
```json
{
  "kind": "entity",
  "value": "javier milei",
  "alert_threshold_sources": 4
}
```

- `kind`: `entity` | `topic` | `all`
- `value`: requerido si `kind` es `entity` o `topic`; ignorado si `kind=all`
- `alert_threshold_sources`: opcional, 2-20

**Response:** `201 Created`, `SubscriptionOut`

**Errors:**
- `400` si `TELEGRAM_CHAT_ID` no está configurado.
- `400` si `kind=entity|topic` y falta `value`.

### `DELETE /subscriptions/{sub_id}`

Elimina una suscripción.

**Path param:** `sub_id`

**Response:** `204 No Content`

**Errors:** `404` si no existe o pertenece a otro chat_id.

---

## Telegram

### `POST /telegram/webhook`

Endpoint que recibe updates de Telegram (modo webhook). Verifica el header `X-Telegram-Bot-Api-Secret-Token` si `TELEGRAM_WEBHOOK_SECRET` está configurado.

**Header:** `X-Telegram-Bot-Api-Secret-Token: <secret>` (cuando está configurado)

**Body:** JSON del update de Telegram (estructura definida por la API de Telegram).

**Response:** `200 OK` `{"ok": true}` — siempre rápido, el procesamiento ocurre en background.

### `POST /telegram/setup-webhook`

Registra la URL de webhook con Telegram.

**Body:**
```json
{
  "url": "https://noticias.tudominio.com/telegram/webhook",
  "drop_pending": false
}
```

**Response:**
```json
{"ok": true, "url": "https://noticias.tudominio.com/telegram/webhook"}
```

**Errors:** `400` si no hay token configurado. `502` si Telegram rechaza la request.

### `POST /telegram/clear-webhook`

Elimina el webhook registrado en Telegram.

**Response:** `{"ok": true}`

**Errors:** `400` / `502` igual que `setup-webhook`.

### `GET /telegram/info`

Información del webhook actual y configuración del bot.

**Response:**
```json
{
  "bot_mode": "webhook",
  "webhook_info": { ... },
  "allowed_chats": ["123456789"]
}
```

**Errors:** `400` si no hay token configurado.

### `POST /digest/send`

Envía el digest de Telegram manualmente.

**Query params:**
- `target` (date, opcional): fecha del briefing. Default: hoy.
- `force` (bool, default `false`): enviar aunque ya se haya enviado antes.

**Response:** `202 Accepted`
```json
{"sent": true, "message_id": 42, "date": "2026-05-09"}
```

**Errors:** `400` si Telegram no está habilitado (`ENABLE_TELEGRAM=false`).
