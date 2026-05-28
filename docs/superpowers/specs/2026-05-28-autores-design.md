# Diseño: Autores, métricas y percepciones

**Fecha:** 2026-05-28
**Estado:** aprobado, pendiente plan de implementación
**Autor:** Lucas Taverna (con asistencia)

## Contexto y motivación

El sistema agrupa notas de los mismos eventos y analiza cómo cada **diario** las cubre. Falta el siguiente nivel de granularidad: **quién** firma esas notas. Conocer al autor habilita preguntas que hoy no se pueden responder:

- ¿Quién cubre más X tema en cada diario?
- ¿Hay autores sistemáticamente más negativos / con más omisiones que el promedio de su diario?
- ¿Cómo cubrieron Pérez (Clarín) y López (Página 12) el mismo cluster?
- ¿Qué autores cubren temas parecidos con sesgos parecidos?

El sistema ya tiene la mayor parte de la infraestructura: extracción de HTML, embeddings, análisis comparativo, tono y bias por diario, y un modelo de datos limpio. Este feature suma autores como entidad de primer nivel y agrega las métricas/UI necesarias.

## Decisiones tomadas

| # | Decisión |
|---|----------|
| 1 | Autor = persona real con byline + autor sintético `"Redacción <Diario>"` para notas sin firma |
| 2 | Extracción: RSS (`dc:creator`) → fallback HTML (`trafilatura.bare_extraction`) → sintético |
| 3 | Coautoría real (N:M con `position`) + canonicalización simple + tabla `author_aliases` para merges manuales |
| 4 | Métricas: M1 (actividad) + M2 (sesgo cuantitativo) + M3 (perfil cualitativo, on-demand) + M4 (comparación entre autores) + Similares (A+B combinados) |
| 5 | UI: byline clickeable en todos lados + página `/authors/:slug` con tabs + comparador con diff narrativo |
| 6 | Umbral de "muestra suficiente" = 3 artículos |

## Arquitectura — qué se agrega

```
RSS feed ──┐
           ├─► fetch.py (dc:creator) ──┐
HTML article ──► extract.py (bare_extraction.author) ──┴─► persist.py
                                                            │
                                                            ▼
                                            authors / article_authors / author_aliases
                                                            │
                                            ┌───────────────┼────────────────┐
                                            ▼               ▼                ▼
                                     /authors/:slug    pipeline:           POST /authors/:slug/
                                        (tabs)         update_author_      profile/regenerate
                                                       vectors             (LLM, on-demand)
                                                       (centroid +
                                                        profile_vector)
                                                            │
                                                            ▼
                                                  /authors/:slug/similar
                                                    /authors/compare
```

Cero cambios en el flujo de embeddings de artículos. Cero llamadas LLM nuevas en el pipeline batch. Las llamadas LLM (M3 y M4) son siempre on-demand.

## Modelo de datos

### Tabla `authors`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | BigInteger PK | |
| `name` | Text | Display name preferido (el más largo visto) |
| `canonical` | Text | `lowercase + sin tildes + sin puntos + spaces collapsed` |
| `source_id` | FK `sources` NULL | Diario primario (primero donde firmó); NOT NULL para sintéticos. Si después firma en otro diario, `source_id` no se reasigna — la métrica "diarios donde escribe" se deriva de `article_authors → articles → source_id`, no de esta columna. |
| `is_synthetic` | Boolean default false | True para "Redacción <Diario>" |
| `first_seen_at` | timestamptz | |
| `last_seen_at` | timestamptz | |
| `article_count` | Integer default 0 | Denormalizado |
| `centroid` | `Vector(1536)` NULL | Promedio de embeddings de sus artículos |
| `profile_vector` | `Vector(20)` NULL | Vector compuesto de perfil estadístico |
| `centroid_updated_at` | timestamptz NULL | Para skip de recompute |
| **Unique** | `(canonical, source_id)` | Permite homónimos en diarios distintos; aliases los unen si son la misma persona |

### Tabla `article_authors`
| Columna | Tipo | Notas |
|---|---|---|
| `article_id` | FK `articles` PK | ON DELETE CASCADE |
| `author_id` | FK `authors` PK | ON DELETE CASCADE |
| `position` | Smallint default 0 | 0 = primary byline, 1+ = coautores |
| Index | `(author_id, article_id)` | Para queries inversas |

### Tabla `author_aliases`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | BigInteger PK | |
| `alias_canonical` | Text Unique | Forma canonicalizada que mapea a otro autor |
| `author_id` | FK `authors` | Autor "real" al que apunta |
| `created_at` | timestamptz | |

Editable manualmente vía SQL/script. No hay UI de aliases.

### Tabla `author_profiles` (M3)
| Columna | Tipo | Notas |
|---|---|---|
| `author_id` | FK `authors` PK | Un perfil por autor |
| `profile_json` | JSONB | Output estructurado del LLM |
| `model` | String(64) | |
| `n_sample` | Integer | Cuántas notas se usaron |
| `generated_at` | timestamptz | |

### Tabla `author_comparisons` (M4b cache)
| Columna | Tipo | Notas |
|---|---|---|
| `id` | BigInteger PK | |
| `author_a_id` / `author_b_id` | FK `authors` | Orden canónico: `a_id < b_id` |
| `comparison_json` | JSONB | Output estructurado del LLM |
| `model` | String(64) | |
| `since` / `until` | Date NULL | Ventana de la comparación (cache key parcial) |
| `generated_at` | timestamptz | |
| **Unique** | `(author_a_id, author_b_id, since, until)` | |

### Migración Alembic
Una migración nueva: cinco tablas + índices. No toca tablas existentes salvo opcionalmente añadir FK helper desde índices ya existentes. Reversible.

## Pipeline — extracción del byline

### Cambios en código existente

**`pipeline/fetch.py`** — `FetchedItem` gana `authors: list[str]`. `parse_feed` lee `entry.author` y `entry.authors` (feedparser ya expone `dc:creator`). Aplica `parse_byline` antes de devolver.

**`pipeline/extract.py`** — Reemplaza `trafilatura.extract()` por `trafilatura.bare_extraction()`. `ExtractedContent` gana `authors: list[str]`. Aplica `parse_byline` sobre `result.author`.

**`pipeline/persist.py`** — Después de insertar/actualizar un `Article`:
1. Combinar `RSS.authors` ∪ `HTML.authors` (RSS prioritario si difieren en orden).
2. Si lista vacía → resolver/crear sintético `"Redacción <source.name>"` con `source_id=src.id`, `is_synthetic=True`.
3. Por cada nombre: canonicalize → buscar en `author_aliases` → resolver a author_id real o crear nuevo en `authors`.
4. Insertar filas en `article_authors` con `position` 0, 1, 2…
5. Skip si ya hay filas en `article_authors` para ese article (idempotencia).

### Módulo nuevo: `pipeline/authors.py`

```python
GENERIC_BYLINES = {"redaccion", "redacción", "agencia", "staff", "editorial", "n/a", ""}

def parse_byline(raw: str) -> list[str]:
    """Split por ' y ', ', ', ' / ', ';'. Strip 'Por ', emails, paréntesis.
    Filter genéricos. Devuelve [] si no quedó nada útil."""

def canonicalize_author(name: str) -> str:
    """Lowercase, remove tildes, strip punctuation, collapse whitespace."""

async def resolve_author(session, *, name: str, source_id: int) -> Author:
    """Lookup por canonical en author_aliases → authors. Crea si no existe."""

async def ensure_synthetic(session, *, source: Source) -> Author:
    """Idempotente. Crea 'Redacción <source.name>' si no existe."""
```

### Backfill

Script `scripts/backfill_authors.py` con flags `--limit N` y `--rate-limit S`. Recorre artículos con `has_full_text=true` y sin filas en `article_authors`, re-descarga HTML solo para metadatos. Corrida única, manual.

## Métricas

### M1 — Actividad (puro SQL)

`GET /authors` — índice con filtros `source`, `q`, `order`, `limit`.

`GET /authors/{slug}/stats`:
```json
{
  "author": {...},
  "totals": {"articles", "clusters", "coauthored", "days_active", "first_seen", "last_seen"},
  "by_topic": [...],
  "by_month": [...],
  "top_entities": [...]
}
```

`GET /sources/{slug}/byline-coverage` — % de notas con firma real vs sintético, por mes. Dato editorial honesto en sí mismo.

### M2 — Sesgo cuantitativo

`GET /authors/{slug}/scorecard?since=&until=`:
```json
{
  "tone": {"avg", "n", "distribution"},
  "framing_diversity": 0.43,
  "omission_rate": 0.18,
  "divergence_score": 0.31,
  "vs_source_baseline": {"tone_delta", "omission_delta"}
}
```

Implementación: refactor menor en `api/analytics.py` para extraer agregaciones reusables a `analytics/_aggregations.py`, parametrizadas por "group by" (diario, entidad, autor). Sin copy-paste.

### M3 — Perfil cualitativo (LLM, on-demand)

`POST /authors/{slug}/profile/regenerate`:
- Input al LLM: hasta 30 análisis más recientes (`Analysis.headline` + `by_source[diario_del_autor]`), no notas completas.
- Output JSON estructurado: `framings_recurrentes`, `fuentes_citadas_frecuentes`, `entidades_dominantes`, `tono_caracteristico`, `temas_evitados`.
- Bloqueado si `n_articulos < 3` (HTTP 400).
- Prompt explícito: "si la muestra no soporta una afirmación, omitila; si la muestra es chica (n<10), marcá los patrones como sugeridos no confirmados".
- Persiste en `author_profiles`. Sobrescribe el anterior.

`GET /authors/{slug}/profile` — devuelve el perfil cacheado o `404`.

### M4 — Comparación entre autores

**M4a — Mismo cluster.** `GET /clusters/{id}/by-author?a=&b=`:
- Devuelve notas de cada autor en ese cluster + análisis comparativo focal.
- Si solo uno cubrió → response explícita ("autor B no cubrió este cluster"), sin forzar comparación.

**M4b — Perfiles enfrentados.** `POST /authors/compare` body `{a, b, since?, until?}`:
- Inputs: M1+M2 de cada autor + M3 si existen.
- Output: síntesis narrativa + listas estructuradas de coincidencias y diferencias.
- Cacheado en `author_comparisons` por `(a_id, b_id, since, until)`. Regenerable.

### Similares (A+B combinados)

**`update_author_vectors`** corre al final del pipeline batch (después de `extract_for_top_clusters`):
- `centroid` = AVG(article.embedding) por author_id, solo si `article_count` cambió desde `centroid_updated_at`.
- `profile_vector` = vector compuesto normalizado:
  - 10 dims: distribución one-hot suave por topic
  - 1 dim: tono promedio normalizado
  - 1 dim: omission_rate
  - 1 dim: divergence_score
  - 1 dim: framing_diversity
  - 6 dims: bucket de actividad mensual reciente
  - Total: 20 dims (paddable, fijo)
- Cero LLM, una pasada SQL + cómputo en Python.

`GET /authors/{slug}/similar?weight_topic=0.5&weight_profile=0.5&limit=10`:
```json
{
  "similar": [
    {"slug", "name", "source", "score", "components": {"topic", "profile"}, "shared_topics": [...]}
  ]
}
```
`score = w1*cosine(centroid) + w2*cosine(profile_vector)`. Si falta `centroid` o `profile_vector` → autor excluido de resultados.

## UI/UX

### Páginas nuevas

**`/authors`** — Índice. Búsqueda, filtros (diario, tema), orden (notas desc default). Lista con: nombre, diario, # notas, tono promedio, último activo. Sintéticos al final, marcados con icono. Badge "muestra suficiente" si `n ≥ 3`.

**`/authors/:slug`** — Perfil con layout B (tabs):
- Header fijo: avatar (iniciales), nombre, diario, # notas, botón "Comparar con otro autor".
- **Tab Resumen** (M1 + Similares): KPIs grandes, gráfico por tema, gráfico actividad mensual, top entidades, sección "Autores parecidos" (oculta si falta `centroid`).
- **Tab Sesgo** (M2): tono distribuido, métricas con `n` visible y tooltip "muestra chica" si `n < 3`, deltas vs baseline del diario.
- **Tab Perfil IA** (M3): botón "Generar perfil" (deshabilitado si `n < 3`); si existe → render del JSON + "Regenerar" + fecha y muestra.
- **Tab Notas**: lista paginada con link a cada cluster.

**`/authors/compare?a=&b=`** — Layout B (diff narrativo):
- Header con ambos autores.
- Síntesis del LLM arriba (bloque destacado).
- Coincidencias (borde verde) / Diferencias (borde rojo).
- Footer: "Ver N clusters compartidos →" → `/authors/compare/clusters?a=&b=`.

**`/authors/compare/clusters?a=&b=`** — Lista de clusters cubiertos por ambos. Cada uno con link a `/clusters/{id}/by-author?a=&b=`.

### Entry points en lo existente

- `ClusterCard`: byline clickeable en cada nota (incluido sintético) → `/authors/:slug`.
- `/clusters/:id`: sección "Autores que cubrieron" arriba. Chips clickeables. Botón "Comparar autores" si ≥2.
- `Header` y `MobileNav`: link "Autores".

### Comportamiento honesto en vacíos

- M1 con `articles < 3` → "datos insuficientes para tendencias".
- M2 con `n < 3` → métrica en gris con tooltip explícito.
- M3 con `n < 3` → botón deshabilitado con tooltip.
- M4 sin overlap → síntesis explícita ("no tienen cobertura compartida").
- Similares sin `centroid` → sección oculta con leyenda.

### Mobile

- Tabs scrollean horizontal en `/authors/:slug`.
- Comparador stackea vertical.
- Chips reusan patrón de `TopicChips`.

## Testing

- **Unit:** `parse_byline` (variantes de split, strip "Por", filtros genéricos, vacío). `canonicalize_author`. Resolución de aliases.
- **Pipeline:** `persist.py` con byline RSS, solo HTML, ninguno (→ sintético), coautoría. Re-procesar artículo no duplica `article_authors`. `update_author_vectors` con autor nuevo y sin cambios.
- **API:** `stats` con n=0, n=2 (debajo umbral), n=20. `profile/regenerate` con n=2 → 400. `compare` sin overlap. `similar` con autor sin centroid → excluido.
- **Smoke frontend:** página renderiza, tabs cambian, gráficos con datos. Vacíos no crashean.
- Patrón existente de pytest en `api/tests/` (209 tests actuales).

## Fuera de alcance explícito (YAGNI)

- Re-extracción automática de bylines cuando cambia HTML upstream.
- Top N autores por sesgo en homepage o digest de Telegram.
- UI para gestionar `author_aliases` (se hace por SQL).
- Autenticación o permisos sobre regenerar perfiles.
- Migración masiva de notas sintéticas a autor real cuando aparezca byline tarde.
- Detección de plagio o reciclado entre autores.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sitios con `dc:creator = "Redacción"` o vacío → muchos sintéticos | Esperable; `byline-coverage` lo hace explícito y honesto |
| Trafilatura devuelve nombres con basura | `parse_byline` strip + heurísticas; casos raros caen al sintético |
| Homónimos en diarios distintos | Unique `(canonical, source_id)` los separa; alias manual los une |
| Umbral n=3 produce perfiles IA débiles | Prompt explícito + badge "muestra chica" en UI |
| `bare_extraction` más lento que `extract` | Insignificante a escala actual |
| Coautoría inconsistente RSS vs HTML | RSS prioritario; documentar en código |
| Backfill tarda (re-descarga HTML) | `--limit` y `--rate-limit`. Corrida única |

## Métrica de éxito

- ≥70% de notas con byline real (no sintético) en los 3 diarios mainstream tras 2 semanas.
- Al menos 20 autores con `n ≥ 10` en el primer mes.
- Calibración cualitativa: comparar 2 autores con intuición previa → ¿el output coincide?
