# Noticias — Plan de extensión de features

> **For agentic workers:** Use superpowers:subagent-driven-development with this plan. Checkboxes (`- [ ]`) for tracking.

**Goal:** Agregar capa de **delivery** (Telegram), **discovery** (search/filter/state), **calidad de clustering** (re-merge/regenerate/sagas) e **insight** (entities/Q&A/trends) sobre la base ya implementada.

**Estado base:** Branch `implementation/initial`. Backend FastAPI funcionando con pipeline completo, frontend Next.js, 7 diarios activos, threshold 0.70, embedding 3-large, top_n 20.

**Spec:** `docs/superpowers/specs/2026-05-08-noticias-design.md`

**Plan original:** `docs/superpowers/plans/2026-05-08-noticias-implementation.md`

---

## Fases (ordenadas por dependencias y valor)

| Fase | Features | Esfuerzo | Dependencias |
|------|----------|----------|--------------|
| A — Delivery | A1 Telegram · A2 Multi-cron · A3 Alertas | ~6h | — |
| B — Discovery/UX | B1 Search · B2 Read state · B3 Topic filter · B4 Annotations · B5 Export | ~10h | B3 antes de B5; otras paralelas |
| C — Clustering | C1 Re-merge · C2 Regen botón · C3 Sagas | ~8h | C1 base de C3 |
| D — Insight | D1 Entities · D2 Compare · D3 Q&A · D4 Sentiment · D5 Bias · D6 Topic sub | ~16h | D1 antes de D5; D4 antes de D5 |

Recomiendo orden: **A1 → A2 → C1 → C2 → B1 → B2 → B3 → C3 → D1 → A3 → D2 → D6 → D4 → D5 → D3 → B4 → B5**.

---

# Fase A — Delivery

## A1: Telegram digest bot

**Goal:** Cada vez que termina un pipeline, mandar un mensaje a Telegram con el briefing del día. Botón manual para forzar reenvío.

### Setup previo (10 min, lo hace el user)

1. Hablar con `@BotFather` en Telegram, crear bot, guardar token.
2. Mandarle un mensaje cualquiera al bot (para que tenga conversación abierta).
3. Visitar `https://api.telegram.org/bot<TOKEN>/getUpdates` — copiar el `chat.id` del JSON.

### Files

- Create: `api/src/noticias_api/notifiers/__init__.py`
- Create: `api/src/noticias_api/notifiers/telegram.py`
- Create: `api/src/noticias_api/notifiers/digest.py`
- Modify: `api/src/noticias_api/config.py` (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM)
- Modify: `api/src/noticias_api/scheduler.py` (post-pipeline hook)
- Modify: `api/src/noticias_api/api/runs.py` (POST /digest/send)
- Modify: `.env.example`
- Migration: agregar tabla `deliveries` para idempotencia
- Tests: `api/tests/test_telegram_notifier.py`, `api/tests/test_digest_send.py`

### Schema delta

```sql
-- Nueva tabla deliveries
CREATE TABLE deliveries (
  id              bigserial primary key,
  channel         text not null,                 -- 'telegram'|'email'|...
  chat_id         text,
  display_date    date not null,
  message_hash    text not null,                 -- sha256 del cuerpo, para detectar cambios
  sent_at         timestamptz default now(),
  status          text not null,                 -- 'sent'|'failed'
  error           text,
  unique(channel, chat_id, display_date, message_hash)
);
```

Migration vía Alembic: `alembic revision -m "add deliveries"`.

### Config

```python
# config.py additions
telegram_bot_token: str | None = None
telegram_chat_id: str | None = None
enable_telegram: bool = False
public_base_url: str = "http://localhost:3000"   # para links en el mensaje
```

`.env.example`:
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ENABLE_TELEGRAM=false
PUBLIC_BASE_URL=http://localhost:3000
```

### Cliente Telegram (telegram.py)

```python
import logging
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TelegramError(Exception): pass


class TelegramClient:
    def __init__(self, bot_token: str, *, timeout: float = 15.0):
        self._url = f"https://api.telegram.org/bot{bot_token}"
        self._timeout = timeout

    async def send_message(
        self, chat_id: str, text: str, *, parse_mode: str = "MarkdownV2",
        disable_web_page_preview: bool = True,
    ) -> int:
        """Returns message_id on success."""
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(
                f"{self._url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                },
            )
        if r.status_code != 200:
            raise TelegramError(f"telegram api {r.status_code}: {r.text[:200]}")
        body = r.json()
        if not body.get("ok"):
            raise TelegramError(f"telegram error: {body.get('description')}")
        return body["result"]["message_id"]


def escape_markdown_v2(s: str) -> str:
    """Telegram MarkdownV2 reserves these chars; escape with backslash."""
    reserved = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in reserved else c for c in s)
```

### Formato del digest (digest.py)

```python
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from noticias_api.db.models import Cluster, Analysis, Article, Source
from noticias_api.notifiers.telegram import escape_markdown_v2 as esc

MAX_LENGTH = 4096   # Telegram message limit


async def build_digest(
    session: AsyncSession, target: date, public_base_url: str
) -> str:
    """Build a Markdown V2 digest message for the given date."""
    clusters = (await session.scalars(
        select(Cluster).where(Cluster.display_date == target)
        .order_by(Cluster.rank_score.desc().nullslast())
    )).all()

    if not clusters:
        return f"📰 *{esc(str(target))}*\n\n_No hay briefing para hoy todavía\\._"

    lines = [f"📰 *Briefing {esc(str(target))}*", ""]
    total_added = 0

    for c in clusters:
        analysis = await session.scalar(
            select(Analysis).where(Analysis.cluster_id == c.id)
        )
        title = (analysis.headline if analysis and analysis.headline
                 else "(análisis pendiente)")
        sources = await session.scalars(
            select(Source.slug).join(Article, Article.source_id == Source.id)
            .where(Article.cluster_id == c.id).distinct()
        )
        slugs = sorted(s for s in sources.all())
        link = f"{public_base_url}/cluster/{c.id}"

        block = (
            f"🎯 *{esc(title)}*\n"
            f"_{c.source_count} diarios · {esc(', '.join(slugs))}_\n"
            f"[Ver detalle]({esc(link)})\n"
        )

        # Truncate if approaching limit
        if total_added + len(block) > MAX_LENGTH - 100:
            lines.append(f"_y {len(clusters) - clusters.index(c)} historias más_\\.\\.\\.")
            break

        lines.append(block)
        total_added += len(block)

    return "\n".join(lines)
```

### Hook post-pipeline (scheduler.py)

Modificar `_run_locked` para que después de un pipeline `success|partial`, dispare el digest si está habilitado:

```python
async def _run_locked(trigger: str, settings: Settings) -> int:
    global _current_run_id
    async with _pipeline_lock:
        ...
        async with async_session_factory() as session:
            run_id = await run_pipeline(session, cfg, trigger=trigger,
                                         openai_client=client)
            _current_run_id = run_id
            # Post-pipeline: send digest if enabled
            if settings.enable_telegram and settings.telegram_bot_token:
                try:
                    await maybe_send_digest(session, settings, run_id)
                except Exception:
                    logger.exception("digest send failed (non-fatal)")
            return run_id
```

`maybe_send_digest` (en digest.py): chequea `deliveries` por `(channel, chat_id, display_date, message_hash)` → si ya se mandó el mismo body, skip. Si no, manda + persiste.

### Endpoint manual (api/runs.py)

```python
@router.post("/digest/send", status_code=202)
async def trigger_digest(
    target: date | None = None,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not settings.enable_telegram:
        raise HTTPException(400, "telegram disabled")
    target = target or date.today()
    msg_id = await send_digest(session, settings, target, force=True)
    return {"sent": True, "message_id": msg_id}
```

### Tests (key cases)

```python
# test_telegram_notifier.py
@pytest.mark.asyncio
async def test_telegram_client_sends(respx_mock):
    respx_mock.post("https://api.telegram.org/bot:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})
    )
    client = TelegramClient(":ABC")
    msg_id = await client.send_message("123", "hola")
    assert msg_id == 42

def test_escape_markdown_v2():
    assert escape_markdown_v2("a.b!") == "a\\.b\\!"
    assert escape_markdown_v2("hola") == "hola"

# test_digest_send.py
@pytest.mark.asyncio
async def test_digest_skips_when_no_clusters(db_session):
    msg = await build_digest(db_session, date.today(), "http://x")
    assert "No hay briefing" in msg

@pytest.mark.asyncio
async def test_digest_idempotent_per_date(db_session, respx_mock, monkeypatch):
    # seed a cluster with analysis
    ...
    respx_mock.post("...").mock(return_value=httpx.Response(200, json={"ok":True,"result":{"message_id":1}}))
    settings = Settings(enable_telegram=True, telegram_bot_token=":ABC", telegram_chat_id="1")
    await send_digest(db_session, settings, date.today())
    await send_digest(db_session, settings, date.today())   # 2nd call should noop
    assert respx_mock.call_count == 1
```

### Effort: ~3-4h

---

## A2: Multi-cron scheduling

**Goal:** Múltiples cron times configurables (ej: 7am, 13:00, 20:00). Cada uno dispara pipeline + digest.

### Files

- Modify: `config.py` — `cron_schedule: str = "0 7,13,20 * * *"` (cron expression con CSV de horas) o lista `cron_hours: list[int] = [7, 13, 20]`
- Modify: `scheduler.py` — leer la lista y registrar un job por hora

### Approach

```python
def setup_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    for hour in settings.cron_hours:
        scheduler.add_job(
            lambda h=hour: asyncio.create_task(_run_locked("cron", settings)),
            CronTrigger(hour=hour, minute=settings.cron_minute),
            id=f"daily_briefing_{hour}",
            replace_existing=True,
        )
    return scheduler
```

Cuidado con la closure de `hour` en lambda — usar default arg.

### Effort: ~30 min

---

## A3: Alertas event-driven

**Goal:** Cuando un cluster nuevo cruza umbrales (ej: ≥4 fuentes, o entidad watched aparece por primera vez), mandar mensaje aparte.

### Files

- Modify: `pipeline/runner.py` — después de `cluster_recent_articles`, emitir eventos de "cluster crossed N sources for first time"
- Create: `notifiers/alerts.py`
- Schema: tabla `watched_entities` (entity_text, alert_chat_id)
- Endpoint: `POST /alerts/watch`, `DELETE /alerts/watch/:id`

### Approach

Después de clusterizar, recorrer clusters cuyos `source_count` recién pasaron umbral:

```python
async def detect_breakouts(session, since: datetime, threshold: int = 4):
    # clusters with source_count >= threshold updated in this run
    rows = await session.scalars(
        select(Cluster).where(Cluster.source_count >= threshold)
        .where(Cluster.last_seen_at >= since)
    )
    for c in rows:
        # only alert once per cluster (track via deliveries)
        already = await session.scalar(
            select(Delivery).where(Delivery.cluster_id == c.id, Delivery.kind == "breakout")
        )
        if not already:
            await send_breakout_alert(c)
```

Para entity-based (D1 dependency): misma lógica pero por presencia de entity.

### Effort: ~2h, depende de D1 si querés alerts por entidad

---

# Fase B — Discovery / UX

## B1: Full-text search

**Goal:** Barra de búsqueda en frontend que busca en titulares, contenido, headlines y common_facts. Usa Postgres FTS español.

### Files

- Migration: `0002_fts.py` — agregar tsvector columns + GIN indexes
- Modify: `api/api/clusters.py` — añadir `GET /search?q=...`
- Modify: `web/components/Header.tsx` — input de búsqueda
- Create: `web/app/search/page.tsx` — resultados

### Schema delta

```python
op.execute("ALTER TABLE articles ADD COLUMN tsv tsvector "
           "GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(content,''))) STORED")
op.execute("CREATE INDEX ix_articles_tsv ON articles USING GIN(tsv)")

op.execute("ALTER TABLE analyses ADD COLUMN tsv tsvector "
           "GENERATED ALWAYS AS (to_tsvector('spanish', "
           "coalesce(headline,'') || ' ' || coalesce(common_facts::text,''))) STORED")
op.execute("CREATE INDEX ix_analyses_tsv ON analyses USING GIN(tsv)")
```

### Endpoint

```python
@router.get("/search")
async def search(q: str, limit: int = 30, session: AsyncSession = Depends(get_session)):
    # Full-text on analyses (preferred) and articles
    query = func.plainto_tsquery('spanish', q)
    cluster_hits = await session.scalars(
        select(Cluster.id).join(Analysis).where(Analysis.tsv.op('@@')(query))
        .order_by(func.ts_rank(Analysis.tsv, query).desc()).limit(limit)
    )
    article_hits = await session.scalars(
        select(Article).where(Article.tsv.op('@@')(query))
        .order_by(func.ts_rank(Article.tsv, query).desc()).limit(limit)
    )
    return {"clusters": list(cluster_hits.all()), "articles": [...]}
```

### UI

Header: input con debounce 300ms, redirige a `/search?q=...`. Página search lista clusters arriba y articles sueltos abajo.

### Effort: ~2-3h

---

## B2: Read state

**Goal:** Marcar clusters como leídos. Visualmente atenuarlos en home.

### Approach simple: localStorage

Guardar en localStorage un Set de cluster IDs leídos. ClusterCard lee este set y aplica `opacity-50` si está leído.

Pros: 0 backend. Privado por dispositivo.
Cons: no syncea entre dispositivos, no persiste si limpian browser.

### Files

- Create: `web/lib/read-state.ts` (read/write to localStorage with key `noticias:read`)
- Modify: `web/components/ClusterCard.tsx` — leer estado, aplicar style
- Add: botón "marcar como leído" en cluster detail page

### Snippet

```ts
const KEY = "noticias:read";
export function getRead(): Set<number> {
  if (typeof window === "undefined") return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(KEY) || "[]"));
  } catch { return new Set(); }
}
export function markRead(id: number) {
  const s = getRead();
  s.add(id);
  localStorage.setItem(KEY, JSON.stringify([...s]));
}
```

ClusterCard se vuelve client component (para leer localStorage). O usamos `next-themes` pattern: el componente principal queda server, un client island maneja la opacidad.

### Effort: ~1h

---

## B3: Topic classification + filter

**Goal:** Cada cluster tiene un campo `topic` (política, economía, deportes, internacional, sociedad, espectáculos). Filtros en home como chips.

### Files

- Schema: `clusters.topic` enum/text
- Migration: `0003_cluster_topic.py`
- Modify: `pipeline/analyze.py` — pedirle al GPT también un topic. O nuevo paso: classify-cluster
- Modify: `pipeline/prompts.py` — agregar field
- Modify: `api/api/briefings.py` — accept `?topic=politica`
- Modify: `web/app/page.tsx` — filter chips

### Approach: extender prompt v2 → v3

Agregar al schema del JSON:

```
"topic": "politica | economia | deportes | internacional | sociedad | espectaculos | otros"
```

Y en pipeline runner, persistir `cluster.topic = result.topic` (no en analyses).

Migrate prompt versions: existing analyses stay v2 sin topic; nuevos son v3 con topic. Para retroactivo: opcional re-analyze.

### UI

```tsx
const TOPICS = ["política", "economía", "deportes", "internacional", "sociedad", "espectáculos"];

<div className="flex gap-2 flex-wrap mb-6">
  {TOPICS.map(t => (
    <Link href={`/?topic=${t}`} key={t}
      className={cn("rounded-full px-3 py-1 text-sm",
        currentTopic === t ? "bg-stone-900 text-white" : "bg-stone-200")}>
      {t}
    </Link>
  ))}
</div>
```

### Effort: ~3h

---

## B4: Annotations

**Goal:** Agregar notas propias a un cluster. Útil para revisitarlo más tarde con contexto.

### Files

- Schema: `cluster_notes` table (cluster_id, note, created_at)
- Endpoints: `POST /clusters/:id/notes`, `GET /clusters/:id/notes`, `DELETE /notes/:id`
- UI: textarea + lista en el detail page

### Schema delta

```sql
CREATE TABLE cluster_notes (
  id          bigserial primary key,
  cluster_id  bigint references clusters(id) on delete cascade,
  note        text not null,
  created_at  timestamptz default now()
);
CREATE INDEX ix_cluster_notes_cluster ON cluster_notes(cluster_id);
```

Sin auth (uso personal). Si después se agrega multi-user, agregar `user_id`.

### Effort: ~2h

---

## B5: Export

**Goal:** Botón "exportar" en cluster detail. Opciones: copiar Markdown al clipboard, download PDF.

### Files

- Modify: `web/components/ClusterDetailPage` — botón export
- Create: `web/lib/export.ts` con `clusterToMarkdown(cluster)` y opcional `clusterToPdf` (con `@react-pdf/renderer` o backend con `weasyprint`)

### Markdown export (simple)

```ts
export function clusterToMarkdown(cluster: ClusterDetail): string {
  const a = cluster.analysis;
  if (!a) return `# ${cluster.id}\nAnálisis pendiente.`;
  let md = `# ${a.headline}\n\n## Hechos en común\n\n`;
  a.common_facts.forEach(f => md += `- ${f}\n`);
  md += `\n## Por diario\n\n`;
  for (const [slug, s] of Object.entries(a.by_source)) {
    md += `### ${slug} (${s.tone})\n\n*${s.framing}*\n\n`;
    s.highlights.forEach(h => md += `- ${h}\n`);
    md += `\n`;
  }
  if (a.divergences.length) {
    md += `## Divergencias\n\n`;
    a.divergences.forEach(d => {
      md += `### ${d.topic}\n`;
      Object.entries(d.positions).forEach(([s, p]) => md += `- **${s}**: ${p}\n`);
    });
  }
  return md;
}
```

Dropdown con "Copiar Markdown" / "Descargar PDF". PDF puede ser una v2.

### Effort: ~1.5h Markdown / +2h para PDF

---

# Fase C — Calidad de clustering

## C1: Re-merge pass

**Goal:** Después del clustering greedy, hacer un segundo pase que mergea clusters cuyos centroids son muy similares. Ataca la fragmentación tipo Adornigate (donde 9 clusters chicos podrían ser 1 grande).

### Approach

Después de `cluster_recent_articles`, recalcular centroids (promedio de embeddings) y mergear pairs con `cosine(centroid_i, centroid_j) >= MERGE_THRESHOLD`. Usar un threshold más conservador que el de articles, ej **0.85**, porque centroids son promedios y por ende menos ruidosos.

### Files

- Modify: `pipeline/cluster.py` — añadir `merge_close_clusters(session, threshold=0.85, window_hours=72)`
- Modify: `pipeline/runner.py` — llamar después de cluster_recent_articles
- Tests: `test_cluster_merge.py`

### Implementación

```python
async def merge_close_clusters(
    session: AsyncSession, *, threshold: float = 0.85, window_hours: int = 72
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    # candidates: clusters with at least one article in window
    cluster_rows = (await session.scalars(
        select(Cluster).where(Cluster.last_seen_at >= cutoff)
    )).all()

    # Recompute centroids from current articles
    for c in cluster_rows:
        embeds = (await session.scalars(
            select(Article.embedding).where(Article.cluster_id == c.id)
            .where(Article.embedding.is_not(None))
        )).all()
        if embeds:
            c.centroid = _mean(embeds)
    await session.commit()

    # Find merge candidates via union-find
    uf = UnionFind([c.id for c in cluster_rows])
    for i, ci in enumerate(cluster_rows):
        for cj in cluster_rows[i+1:]:
            if ci.centroid and cj.centroid:
                sim = 1 - cosine_distance(ci.centroid, cj.centroid)
                if sim >= threshold:
                    uf.union(ci.id, cj.id)

    # Apply merges: pick smallest cluster_id as canonical
    merges = 0
    for cid in [c.id for c in cluster_rows]:
        canonical = uf.find(cid)
        if canonical != cid:
            await session.execute(
                update(Article).where(Article.cluster_id == cid)
                .values(cluster_id=canonical)
            )
            await session.execute(delete(Cluster).where(Cluster.id == cid))
            merges += 1
    await session.commit()
    await _refresh_cluster_stats(session, cutoff)
    return {"merged": merges}
```

### Tests

- Two clusters with very similar centroids → merge
- Two with dissimilar centroids → no merge
- Merge cascades stats (article_count, source_count)
- Idempotent: running twice doesn't merge again

### Effort: ~3h

---

## C2: Botón "regenerar análisis" por cluster

**Goal:** En cluster detail, botón que borra el `Analysis` y dispara una re-análisis (sin correr todo el pipeline).

### Files

- Endpoint: `POST /clusters/:id/regenerate-analysis`
- UI: botón en cluster detail
- Reuso: la función `_analyze_top_clusters` ya hace lo que necesitamos para 1 cluster

### Endpoint

```python
@router.post("/clusters/{cluster_id}/regenerate-analysis")
async def regenerate(cluster_id: int, settings: Settings = Depends(get_settings),
                     session: AsyncSession = Depends(get_session)):
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(404)
    await session.execute(delete(Analysis).where(Analysis.cluster_id == cluster_id))
    await session.commit()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    cfg = pipeline_config_from(settings)
    # Call _analyze_top_clusters but for just this cluster — refactor to take optional id
    cluster.is_top = True   # ensure it's analyzed
    await session.commit()
    await _analyze_top_clusters(session, client, cfg)
    return {"regenerated": True}
```

(O refactorear `_analyze_top_clusters` para aceptar `cluster_ids: list[int] | None = None`.)

### UI

Botón pequeño "↻ Regenerar análisis" en el header del cluster detail page. Click → loading → router.refresh().

### Effort: ~1.5h

---

## C3: Saga clustering (multi-day)

**Goal:** Clusters de varios días que tratan del mismo "tema overarching" (ej: Adornigate-Bullrich-Caputo-UBA → "Saga Adornigate"). Briefing podría tener una sección "sagas en desarrollo".

### Schema

Nueva tabla `sagas`:
```sql
CREATE TABLE sagas (
  id              bigserial primary key,
  title           text not null,
  centroid        vector(1536),
  first_seen_at   timestamptz default now(),
  last_seen_at    timestamptz default now(),
  cluster_count   int default 0,
  source_count    int default 0,
  article_count   int default 0
);
ALTER TABLE clusters ADD COLUMN saga_id bigint references sagas(id) on delete set null;
CREATE INDEX ix_clusters_saga ON clusters(saga_id);
```

### Approach

Después de cada pipeline:
1. Para cada cluster, calcular su centroid si no está
2. kNN con OTROS centroids de cluster en ventana 7 días (no solo 48h)
3. Si sim >= 0.80 con un cluster que ya tiene saga → unir saga
4. Si dos clusters comparten saga_id → no acción
5. Si dos clusters sin saga matchean → crear saga nueva

Reuso de pgvector. Misma estructura que clustering normal, distinto threshold y window.

### UI

- Nueva sección en home: "Sagas en desarrollo" (clusters agrupados por saga)
- En cluster detail: chip "Forma parte de saga: Adornigate" → link a la página saga

### Effort: ~5h, depende de C1 (re-merge funcional para evitar fragmentación inicial)

---

# Fase D — Insight & análisis

## D1: Entity extraction + browsing

**Goal:** Extraer personas, organizaciones, lugares de cada cluster. Dashboard de entidades. Click en una entidad → todos los clusters que la mencionan.

### Approach

Agregar paso al pipeline después de analysis: pedirle al GPT (o usar spaCy multilingual) los entities. Persistir.

#### Schema

```sql
CREATE TABLE entities (
  id          bigserial primary key,
  name        text not null,
  kind        text not null,           -- 'person'|'org'|'place'|'event'
  canonical   text,                    -- normalized form (e.g., "Manuel Adorni" canon for "Adorni")
  unique(name, kind)
);
CREATE TABLE cluster_entities (
  cluster_id  bigint references clusters(id) on delete cascade,
  entity_id   bigint references entities(id) on delete cascade,
  mention_count int default 1,
  primary key (cluster_id, entity_id)
);
CREATE INDEX ix_entities_canonical ON entities(canonical);
```

#### Pipeline step

```python
# nuevo paso: extract_entities
async def extract_entities_for_cluster(client, cluster_text):
    prompt = """Extract named entities. Return JSON:
    {"persons": ["Manuel Adorni", ...], "orgs": [...], "places": [...]}"""
    ...
```

Costo: 1 llamada chica (gpt-4o-mini) por cluster top. ~$0.001/cluster.

Alternativa más barata: spaCy `es_core_news_md` local. Tradeoff: peor para Argentina-specific entities (políticos, etc.).

Recomendación: GPT-4o-mini (más exacto, costo trivial).

#### UI

- `/entities` — lista paginada con count de menciones
- `/entities/:slug` — clusters mencionando (timeline)
- En cluster detail: chips de entities → link

### Effort: ~5h

---

## D2: Compare view (split-screen)

**Goal:** Pantalla de comparación lado a lado de DOS clusters relacionados o de DOS diarios sobre el mismo cluster.

### Files

- Create: `web/app/compare/page.tsx?a=clusterA&b=clusterB`
- Create: `web/app/cluster/[id]/compare/[other]/page.tsx`

### Approach

Layout 2 columnas. Headers: 2 headlines lado a lado. Hechos en común: union de ambos. Por diario: side-by-side panels. Divergencias: si comparten cluster, las divergencias son las del análisis. Si son clusters distintos, mostrar entity overlap.

Para "comparar dos diarios sobre mismo cluster": ya está el cluster detail, solo agregar un toggle "ver lado a lado".

### Effort: ~2h

---

## D3: AI Q&A sobre el corpus (RAG)

**Goal:** Pregunta libre sobre el archivo. "¿Qué dijo La Nación sobre Adorni esta semana?" → resumen sintetizado con citas.

### Approach

Standard RAG:
1. User query → embedding
2. kNN over articles + analyses → top 20 chunks
3. Stuff into context window of GPT-4o
4. Stream answer with citations

### Files

- Create: `api/src/noticias_api/api/qa.py` — `POST /qa { query }` retorna `{ answer, sources: [{cluster_id, source, quote}] }`
- Create: `web/app/qa/page.tsx` — chat-like UI
- Optional: persistir `qa_sessions` para histórico

### Snippet

```python
async def answer_query(client, session, query: str) -> QAResult:
    [emb] = await embed_texts(client, [query], model=settings.embedding_model)
    # kNN
    rows = await session.execute(
        select(Article, Source, Cluster)
        .join(Source, Article.source_id == Source.id)
        .join(Cluster, Article.cluster_id == Cluster.id)
        .where(Article.embedding.is_not(None))
        .order_by(Article.embedding.cosine_distance(emb))
        .limit(20)
    )
    chunks = [
        f"[{i+1}] {src.slug} ({a.published_at:%Y-%m-%d}): {a.title}\n{a.content[:1500] or a.summary}\n"
        for i, (a, src, c) in enumerate(rows.all())
    ]
    prompt = f"""Respondé la pregunta del usuario usando SOLO los siguientes
    fragmentos. Citá con [N] inline. Si la respuesta no está, decí que no la
    encontraste.

    Pregunta: {query}

    Fragmentos:
    {chr(10).join(chunks)}
    """
    response = await client.chat.completions.create(
        model="gpt-4o", messages=[{"role":"user","content":prompt}], stream=True
    )
    return ...
```

### UI

Streaming response usando SSE o simple polling. Citas clickeables → cluster detail.

### Effort: ~5h

---

## D4: Sentiment trends chart

**Goal:** Gráfico de tono de cada diario sobre temas/entidades a lo largo del tiempo. Ej: "% de notas sobre Milei con tono crítico/favorable, por diario, últimos 30 días".

### Approach

Aprovecha el campo `tone` que ya guarda analyses. No necesita nuevo cómputo.

### Files

- Endpoint: `GET /analytics/tone-by-source?entity=Milei&since=2026-04-01`
- UI: `/analytics` con un chart (recharts o similar)

### Endpoint

```python
@router.get("/analytics/tone-by-source")
async def tone_by_source(entity: str | None = None, since: date | None = None,
                         session: AsyncSession = Depends(get_session)):
    # Usa entity (D1) si filtramos. Sin entity, todos los clusters.
    q = select(...).select_from(Analysis).join(Cluster).join(Article).join(Source)
    if entity:
        q = q.join(ClusterEntity).join(Entity).where(Entity.canonical == entity)
    if since:
        q = q.where(Cluster.display_date >= since)
    # Agrupar: por (source, week, tone) → count
    ...
```

### UI

Stacked bar chart por semana, una columna por diario, segmentos por tono coloreado (verde/rojo/amarillo/gris). Recharts es fácil:

```tsx
<BarChart data={data}>
  <XAxis dataKey="week" />
  <Bar dataKey="favorable" stackId="a" fill="#10b981" />
  <Bar dataKey="critico" stackId="a" fill="#f43f5e" />
  ...
</BarChart>
```

### Effort: ~3h, depende de D1 si querés filtro por entidad

---

## D5: Bias scorecard

**Goal:** Métrica acumulativa: "La Nación: 60% notas críticas de Milei, 20% favorables. Página 12: 5% favorables, 80% críticas". Tabla de comparación rápida.

### Approach

Es D4 pero presentado como tabla scoreboard, no chart. Mismo backend.

```
                  Milei            Massa            Bullrich
La Nación        🟢40 🔴30        🔴60 🟢10        🟢55 🔴20
Página 12        🔴85 🟢2         🟢45 🔴15        🔴60 🟢10
```

### Files

- UI: `/analytics/bias` — grid de heatmap

### Effort: ~2h, depende de D1 + D4

---

## D6: Topic subscriptions

**Goal:** El digest de Telegram filtra solo a temas/entidades que te interesan. Configurable desde UI.

### Files

- Schema: `subscriptions` table (channel, kind=topic|entity, value, chat_id)
- UI: `/subscriptions` — agregar/quitar
- Modify: `notifiers/digest.py` — filtra clusters por subs antes de armar mensaje

### Schema

```sql
CREATE TABLE subscriptions (
  id          bigserial primary key,
  channel     text not null,           -- 'telegram'
  chat_id     text not null,
  kind        text not null,           -- 'topic'|'entity'|'all'
  value       text,                    -- 'politica' o 'Manuel Adorni' o NULL si kind=all
  created_at  timestamptz default now()
);
```

### Build digest filtered

```python
async def build_filtered_digest(session, target, public_base_url, chat_id):
    subs = await session.scalars(
        select(Subscription).where(Subscription.chat_id == chat_id)
    )
    sub_list = list(subs.all())
    if not sub_list or any(s.kind == 'all' for s in sub_list):
        return await build_digest(session, target, public_base_url)
    # Otherwise filter clusters
    topic_filter = {s.value for s in sub_list if s.kind == 'topic'}
    entity_filter = {s.value for s in sub_list if s.kind == 'entity'}
    clusters = (await session.scalars(
        select(Cluster).where(...).where(or_(
            Cluster.topic.in_(topic_filter) if topic_filter else False,
            Cluster.id.in_(
                select(ClusterEntity.cluster_id).join(Entity).where(Entity.canonical.in_(entity_filter))
            ) if entity_filter else False,
        ))
    )).all()
    ...
```

### Effort: ~3h, depende de B3 + D1

---

# Resumen visual de dependencias

```
A1 Telegram digest ──┬─ A2 Multi-cron (independent extension)
                     └─ D6 Topic sub (filters digest)
                          └─ depends on B3 + D1

B1 Search (independent)
B2 Read state (independent)
B3 Topic filter ──── D6
B4 Annotations (independent)
B5 Export (independent)

C1 Re-merge ─── C3 Saga clustering
C2 Regenerate (independent)

D1 Entities ──┬── D4 Sentiment trends ── D5 Bias
              ├── A3 Entity-based alerts
              └── D6 Topic/entity sub

D2 Compare (independent)
D3 AI Q&A (depends on existing embeddings, otherwise standalone)
```

# Effort total estimado

| Fase | Horas |
|------|-------|
| A | 6 |
| B | 10 |
| C | 8 |
| D | 16 |
| **Total** | **40h** |

40h spread como ~1-2 horas por feature en promedio. Algunas (D3 RAG, D1 entities) son las más densas.

# Orden de ejecución recomendado

Si querés ir consecutivo y aprovechar momentum:

1. **A1 Telegram** (gana valor inmediato)
2. **C1 Re-merge** (fix calidad, hace el resto más útil)
3. **B1 Search** + **B2 Read state** (quick wins UX)
4. **A2 Multi-cron** (5 min)
5. **B3 Topic filter** (cambia mucho la usabilidad)
6. **C2 Regenerate** (utility chico)
7. **D1 Entities** (foundation de varias)
8. **D6 Topic sub + A3 Alerts** (ahora que tenés los building blocks)
9. **D4 Sentiment** + **D5 Bias** (insights basados en data ya acumulada)
10. **D2 Compare** + **B4 Annotations** + **B5 Export** (nice-to-haves)
11. **C3 Saga** + **D3 Q&A** (más ambiciosos, dejar para después)

Cada bloque del orden mantiene un release-able state — podés parar en cualquier punto y tener algo bien.
