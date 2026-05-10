# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.0] — 2026-05-09

### Added

- **RAG upgrades**: memoria de conversación (`qa_messages`), HyDE (gpt-4o-mini), Cohere reranking (rerank-multilingual-v3.0), CRAG-lite para veredictos de relevancia por chunk
- **Q&A multi-turno**: `conversation_id` persistente en web (`localStorage`) y bot Telegram (`telegram:{chat_id}`)
- **Badge de cobertura** en la UI de Q&A: ✓ confident / △ partial / ○ empty según veredicto CRAG
- **`GET /qa/history`**: endpoint para recuperar el historial de una conversación
- **Mobile responsive**: hamburger nav drawer, ícono de búsqueda en header mobile, BiasScorecard como cards en mobile y tabla en desktop
- **PWA instalable**: `manifest.json` + íconos + apple-touch-icon; instalable desde iOS/Android
- Safe-area insets para notch de iOS; tamaños de botón touch-friendly (`min-h-[44px]`)
- Suite de documentación técnica completa (arquitectura, API ref, guía de usuario, dev guide)

### Fixed

- Analytics endpoints: bounds UTC-aware (antes excluía datos después de medianoche UTC local)
- Q&A CORS: llamadas del browser ahora pasan por proxy Next.js en `/api/qa` y `/api/qa/history`

### Changed

- `POST /qa` body: ahora acepta `conversation_id` (opcional)
- `POST /qa` response: ahora incluye `conversation_id`, `hyde_query`, `confidence`, `crag_verdicts`
- `/qa` es stateful por `conversation_id`; el comportamiento de sesión única (sin conversation_id) sigue funcionando igual
- Bot Telegram Q&A: usa memoria persistente por chat (últimos 6 turnos por defecto)

---

## [0.2.0] — 2026-05-09

### Added

- **Bot de Telegram** con Q&A libre sobre el corpus (RAG: pgvector + GPT-4o synthesis)
- **Digest Telegram** con idempotencia por hash de mensaje; alertas en tiempo real por suscripción
- **Suscripciones** filtradas por entidad, tema o sin filtro, con umbral de fuentes para alertas
- **Entidades nombradas**: extracción con GPT-4o-mini (persona, org, lugar, evento) + canonicalización + navegación por entidad
- **Sagas**: agrupación de clusters multi-día con Union-Find sobre ventana de 7 días
- **Q&A web** (`/qa`): preguntas en lenguaje natural con citas numeradas y links
- **Analytics**: tendencias de tono por diario (últimos 30 días) + bias scorecard fuente × entidad
- **Búsqueda FTS** (`/search`): texto completo sobre títulos, contenido y análisis (diccionario español)
- **Filtro por tema**: clasificación con GPT-4o-mini en 7 categorías + chips de filtro en el briefing
- **Anotaciones**: notas libres por cluster, persistidas en DB
- **Exportar Markdown**: descarga del análisis completo de un cluster
- **Comparar**: vista lado a lado de dos clusters (`/compare?a=N&b=N`)
- **Segunda pasada de merge**: fusión de clusters con centroides similares (Union-Find, umbral 0.85)
- Endpoint `POST /clusters/{id}/regenerate-analysis` para forzar re-análisis puntual
- `GET /runs/current` para polling del pipeline en ejecución

### Changed

- Prompt de análisis actualizado a v2: más detalle en highlights (5-7 puntos por fuente), framing más concreto, reglas explícitas contra generalidades
- Umbral de clustering bajado de 0.78 a 0.70 para capturar más variantes de un mismo hecho
- Embedding model: `text-embedding-3-large` con `dimensions=1536` (mayor calidad semántica)

---

## [0.1.0] — 2026-05-08

### Added

- **Pipeline core**: fetch RSS → extract (trafilatura) → embed (text-embedding-3-large) → cluster kNN greedy → rank → analyze (GPT-4o)
- **9 fuentes**: La Nación, Clarín, Infobae (mainstream), Página 12, Tiempo Argentino, El Destape (crítico), Ámbito, El Cronista, BAE Negocios (económico)
- **Frontend Next.js 15**: briefing del día, detalle de cluster, historial de fechas, página de fuentes
- **API FastAPI** con endpoints para briefings, clusters, sources, runs
- **Análisis editorial** por cluster: hechos en común, por diario (highlights + framing + tono), omisiones, divergencias
- **State de lectura** persistido en localStorage
- **Pipeline manual** vía botón "Actualizar" en el frontend
- **Pipeline automático** via APScheduler (cron configurable por hora)
- **8 migraciones Alembic**: schema inicial, deliveries, FTS, sagas, entities, subs+alerts, cluster_topic, cluster_notes
- **169 tests** con pytest-asyncio + pytest-postgresql + respx
- Docker Compose con postgres (pgvector), api y web
- Script de backup con rotación automática

---

[0.3.0]: https://github.com/Ltaverna/brief_noticias/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Ltaverna/brief_noticias/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Ltaverna/brief_noticias/releases/tag/v0.1.0
