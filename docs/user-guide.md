# Guía de usuario

Todo lo que necesitás saber para usar Noticias. Para setup técnico, ver [development.md](development.md).

---

## Página principal (Briefing del día)

La página principal muestra el **briefing de hoy**: los clusters de noticias más relevantes, ordenados por importancia (fuentes × diversidad × recencia).

### Las tarjetas (cluster cards)

Cada tarjeta representa un **cluster**: un grupo de artículos de distintos diarios sobre el mismo hecho.

```
┌─────────────────────────────────────────────────────┐
│ Milei cierra acuerdo con el FMI por USD 20 mil      │ ← titular neutral generado por GPT-4o
│ millones tras meses de negociación                  │
│                                                     │
│ 6 diarios · 3 puntos de divergencia                 │ ← cuántos medios + cuántas divergencias detectadas
│                                                     │
│ [política]  [clarín]  [La Nación]  [Infobae]        │ ← chip de tema + chips de fuentes
│                                              ○ / ✓  │ ← botón de leído
└─────────────────────────────────────────────────────┘
```

**Qué significa cada elemento:**

- **Titular**: generado por GPT-4o a partir de todos los artículos del cluster. Intenta ser neutral.
- **N diarios**: cuántas fuentes distintas cubren el hecho.
- **N puntos de divergencia**: cuántos desacuerdos factuales o interpretativos detectó el modelo.
- **Chip de tema**: la categoría del cluster (política, economía, deportes, etc.).
- **Chips de fuentes**: qué diarios tienen artículos en el cluster. El color identifica el grupo editorial (azul = mainstream, rojo = crítico, verde = económico).
- **○ / ✓**: marca el cluster como leído/no leído (se guarda en el navegador).

### Filtro por tema

Debajo del encabezado hay chips para filtrar por tema:

```
[Todas]  [Política]  [Economía]  [Internacional]  [Sociedad]  [Deportes]  [Espectáculos]  [Otros]
```

Al hacer clic en un tema, la URL cambia a `/?topic=politica` y solo se muestran los clusters de esa categoría. El filtro se puede combinar con el historial de fechas.

### Botón Actualizar

En el margen superior derecho. Dispara el pipeline manualmente (fetch RSS → embedding → clustering → análisis GPT-4o). Mientras corre, el botón muestra el estado. Normalmente el pipeline corre automáticamente a las 7:00 AM.

---

## Detalle de un cluster

Al hacer clic en una tarjeta se abre la página `/cluster/{id}` con el análisis completo.

### Encabezado

- **Titular**: el headline generado.
- **N diarios · N artículos**: resumen de cobertura.
- **Saga badge**: si el cluster pertenece a una saga (historia multi-día), aparece un link a esa saga.
- **Chips de entidades**: personas, organizaciones, lugares y eventos mencionados (extraídos por GPT-4o-mini). Al hacer clic se abre la página de la entidad.
- **Botones de acción**: marcar leído, regenerar análisis, exportar como Markdown.

### Sección: Hechos en común

Lista de hechos concretos que **todos los diarios** reportan. Son afirmaciones declarativas verificadas por el modelo, por ejemplo:

```
• El acuerdo fue firmado el lunes 8 de mayo
• El monto total es de USD 20.000 millones
• La negociación duró seis meses
```

Son el punto de partida neutral antes de ver las diferencias editoriales.

### Sección: Por diario

Tabs o paneles, uno por cada diario que cubrió el hecho. Para cada diario el modelo produce:

- **Highlights** (5-7 puntos): lo que ese diario destaca específicamente — datos, declaraciones entrecomilladas, ángulo editorial, fuentes citadas. Más detallado que los hechos en común.
- **Framing**: 3-4 oraciones sobre cómo encuadra el hecho ese diario: quién es el protagonista, qué causa atribuye, qué consecuencia destaca, qué juicio implícito o explícito tiene.
- **Tono**: una de `neutral | crítico | favorable | alarmista | celebratorio | escéptico | otro`.

Los paneles tienen borde de color según el tono: verde para favorable/celebratorio, rojo para crítico/alarmista, gris para neutral/escéptico.

### Sección: Omisiones

Lo que un diario **no menciona** pero sí está presente en otros. Ejemplo:

```
• infobae omite: el impacto en jubilaciones, presente en todos los demás
• pagina12 omite: la fecha concreta del inicio del pago
```

Las omisiones son un indicador directo de sesgo editorial por silencio.

### Sección: Divergencias

Puntos donde los diarios **no coinciden**: datos distintos, atribuciones opuestas, interpretaciones enfrentadas. Se muestran como tabla:

| Punto en disputa | Clarín | Página 12 |
|-----------------|--------|-----------|
| Monto acordado | "USD 20.000 millones en tres tramos" | "La cifra real sería la mitad según fuentes del FMI" |

La tabla permite comparar de un vistazo las posturas de cada diario sobre el mismo punto.

### Sección: Artículos fuente

Lista de todos los artículos que conforman el cluster, con link al original, nombre del diario y un indicador si solo se pudo obtener título/resumen (sin texto completo).

### Notas del cluster

Al final de la página hay un campo para agregar anotaciones libres al cluster. Las notas se guardan en la base de datos y son visibles en todas las sesiones.

---

## Historial de fechas

La página `/historial` lista todos los días con briefing disponible. Al hacer clic en una fecha se abre `/briefing/{fecha}` con el briefing de ese día, también con filtro por tema.

---

## Sagas

Las **sagas** son historias que se extienden más de un día. Si varios clusters de días distintos tratan el mismo tema en curso (por ejemplo, un juicio, una negociación, un conflicto), el sistema los agrupa en una saga.

### Dónde aparecen

- En el encabezado de un cluster, si ese cluster forma parte de una saga.
- En la página `/sagas`, con la lista de todas las sagas activas ordenadas por actividad reciente.
- En `/saga/{id}` con el detalle: todos los clusters que la componen.

### Qué diferencia una saga de un cluster

| | Cluster | Saga |
|--|---------|------|
| Alcance temporal | Horas (ventana de 48h) | Días o semanas (ventana de 7 días) |
| Contenido | Artículos del mismo hecho puntual | Clusters de una historia en curso |
| Análisis GPT | Sí | No (agrupa los análisis existentes) |

---

## Entidades

La página `/entities` lista personas, organizaciones, lugares y eventos mencionados en los clusters analizados.

### Tipos de entidades

| Tipo | Ejemplos |
|------|---------|
| `person` | Manuel Adorni, Patricia Bullrich |
| `org` | FMI, Banco Central, YPF |
| `place` | Casa Rosada, Buenos Aires, Washington |
| `event` | Adornigate, Mundial 2026 |

### Filtros

En la barra superior podés filtrar por tipo y buscar por nombre. El orden por default es por `cluster_count` descendente (las entidades más mencionadas primero).

### Detalle de una entidad

Al hacer clic en una entidad se abre `/entities/{id}` con todos los clusters donde fue mencionada, ordenados por fecha de última aparición.

---

## Estado de lectura (○ / ✓)

El botón ○/✓ en cada tarjeta marca si ya leíste ese cluster. El estado se guarda en `localStorage` del navegador — no requiere cuenta ni servidor. Se usa para reducir el ruido visual en clusters ya revisados (aparecen con menos opacidad).

---

## Búsqueda

La página `/search` y el campo de búsqueda en el header permiten buscar en el corpus usando **búsqueda de texto completo** (Postgres FTS con diccionario español).

### Qué cubre la búsqueda

- Headlines y hechos en común de los análisis
- Títulos y contenido de los artículos

### Resultados

Los resultados se dividen en dos listas:

1. **Clusters**: análisis que coinciden con la búsqueda (headline o common_facts).
2. **Artículos**: artículos individuales que coinciden.

Ambas listas incluyen un puntaje de relevancia (`ts_rank`) y link a la página de detalle. La búsqueda es insensible a acentos y maneja morfología española (lematización).

---

## Q&A — Preguntar al corpus

La página `/qa` permite hacer preguntas en lenguaje natural sobre el corpus de artículos indexados. La interfaz es conversacional: cada pregunta es un turno en el mismo hilo, y podés hacer seguimientos sin repetir el contexto.

### Conversación multi-turno

Las preguntas se encadenan automáticamente dentro de una sesión del navegador. El sistema recuerda los últimos turnos de la conversación:

```
Vos: ¿Qué dijo Clarín sobre el acuerdo con el FMI?
Bot: Clarín destacó que el acuerdo fue firmado el lunes [1]...

Vos: ¿Y Página 12?
Bot: Página 12 cuestionó el monto real del acuerdo [2]...
```

Para empezar una conversación nueva (olvidar el hilo anterior), hacer clic en el botón **"Nueva conversación"**.

### Badge de cobertura

Debajo de cada respuesta aparece un badge que indica qué tan bien cubierta está la pregunta en el corpus:

| Badge | Significado |
|-------|-------------|
| ✓ Cobertura buena | El pipeline encontró al menos 3 artículos claramente relevantes. |
| △ Cobertura parcial | Solo 1-2 artículos relevantes. La respuesta puede ser incompleta. |
| ○ Sin cobertura | No se encontró información relevante. El sistema lo indica sin inventar. |

### Cómo funciona (simplificado)

1. Tu pregunta se transforma en una "respuesta hipotética" con estilo periodístico (HyDE), que sirve como vector de búsqueda más preciso.
2. Se recuperan los artículos más cercanos semánticamente (hasta 50 candidatos).
3. Un reranker de Cohere selecciona los 10 más relevantes (si `COHERE_API_KEY` está configurado).
4. CRAG-lite evalúa chunk por chunk si el material es realmente pertinente.
5. GPT-4o sintetiza la respuesta con citas numeradas `[N]`.
6. La conversación se guarda para que el siguiente turno tenga contexto.

### Ejemplos de preguntas

```
¿Qué dijo La Nación esta semana sobre Adorni?
¿Cuáles son las distintas versiones sobre el acuerdo con el FMI?
¿Qué cobertura dio Página 12 a la negociación?
¿Y Clarín?  ← pregunta de seguimiento sin repetir el tema
```

### Límites

- Solo cubre el corpus indexado (artículos en la base de datos).
- Si la respuesta no está en el corpus, el badge "Sin cobertura" aparece y el modelo no inventa.
- No usa conocimiento externo al corpus.

---

## Analytics

### Tendencias de tono (`/analytics`)

Gráfico de barras con la distribución de tonos (`neutral`, `crítico`, `favorable`, etc.) por diario a lo largo del tiempo. Por default muestra los últimos 30 días agrupados por semana.

**Filtros disponibles:**

- **Entidad**: podés filtrar por entidad canónica (ej: `manuel adorni`) para ver cómo cada diario la trató.
- **Granularidad**: semana (`week`) o día (`day`).

### Bias scorecard (`/analytics/bias`)

Tabla cruzada fuente × entidad que muestra cuántas veces cada diario cubrió una entidad con tono favorable, crítico o neutral. Útil para detectar patrones sistemáticos de cobertura.

**Filtros:** tipo de entidad (`person`, `org`, `place`, `event`), cantidad de entidades top (2-20), fecha de inicio.

---

## Suscripciones

La página `/subscriptions` permite configurar qué llega al digest de Telegram.

### Tipos de suscripción

| Tipo | `value` | Efecto |
|------|---------|--------|
| `all` | — | El digest completo sin filtro |
| `topic` | Ej: `politica` | Solo clusters de ese tema |
| `entity` | Ej: `manuel adorni` | Solo clusters donde aparece esa entidad |

### Alertas

Cada suscripción puede tener un `alert_threshold_sources` (2-20). Cuando un cluster nuevo cruza ese umbral de fuentes y coincide con el filtro, se envía una notificación inmediata al chat (sin esperar el digest).

### Notas

- Las suscripciones se asocian al `TELEGRAM_CHAT_ID` configurado en el servidor.
- Si no hay suscripciones activas, el digest envía todos los clusters del día.
- Para eliminar una suscripción, hacer clic en "quitar".

---

## Bot de Telegram

El bot responde mensajes en el chat configurado.

### Comandos

| Comando | Efecto |
|---------|--------|
| `/start` | Mensaje de bienvenida |
| `/help` | Lista de comandos disponibles |

### Preguntas libres

Cualquier mensaje que no sea un comando se trata como una pregunta al corpus (Q&A). El bot usa el mismo pipeline RAG que la página `/qa` — con HyDE, reranking y CRAG-lite — y retorna la respuesta con citas como links clickeables.

```
Usuario: ¿Qué dijo Clarín sobre el acuerdo con el FMI?

Bot: Clarín destacó que el acuerdo fue anunciado el lunes
     por el ministro de Economía [1] y que el monto total
     asciende a USD 20.000 millones en tres tramos [2].

     Fuentes
     [1] clarin - 2026-05-08
     [2] clarin - 2026-05-07

Usuario: ¿Y Página 12?

Bot: Página 12 cuestionó el monto real, citando fuentes del FMI [3]...
```

**Memoria por chat:** cada conversación de Telegram tiene su propio historial persistente. El bot recuerda los últimos 6 turnos del chat, por lo que las preguntas de seguimiento funcionan igual que en la interfaz web.

### Modes

El bot soporta dos modos configurables via `TELEGRAM_BOT_MODE`:

- `webhook`: Telegram envía actualizaciones al endpoint `/telegram/webhook`. Requiere URL pública (ver [deployment.md](deployment.md)).
- `polling`: La API hace long-polling a Telegram. Útil en desarrollo local sin URL pública.
- `off`: Bot deshabilitado.

---

## Notas de cluster

En la página de detalle de un cluster hay una sección "Notas" donde podés agregar anotaciones libres (hasta 2000 caracteres). Las notas:

- Se guardan en la base de datos.
- Son visibles para todos los usuarios de la instancia (no hay autenticación por usuario).
- Se pueden eliminar individualmente.

---

## Exportar como Markdown

En la página de detalle de un cluster, el botón "Exportar" descarga un archivo `.md` con el análisis completo: headline, hechos en común, análisis por diario (tone + framing + highlights), omisiones, divergencias y links a artículos fuente.

---

## Comparar dos clusters

La URL `/compare?a={id}&b={id}` abre una vista lado a lado de dos clusters. Útil para comparar cómo se cubrió el mismo tema en días distintos o contrastar dos historias relacionadas.

---

## Ver también

- [Arquitectura](architecture.md) — cómo funciona el pipeline por dentro
- [API Reference](api-reference.md) — endpoints disponibles
- [Development](development.md) — cómo extender el sistema
