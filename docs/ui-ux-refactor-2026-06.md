# UI/UX Refactor — Frontend `web/` (2026-06-02)

Análisis crítico del front + implementación de mejoras de accesibilidad y diseño.
Stack: **Next.js 15 (App Router) · React 19 · Tailwind v4 · next-themes**.

- **Commit:** `cccc98f` — `feat(web): a11y + design polish pass` (en `origin/main`)
- **Verificación:** `tsc --noEmit` ✅ exit 0 · `next build` ✅ "Compiled successfully"
- **Deploy:** ⛔ pendiente — bloqueado por infra del host (ver §5), **no por el código**

---

## 1. Lo que ya estaba bien (no se tocó)

- Sistema tipográfico correcto: **Newsreader** (serif, titulares) + **Inter** (sans, cuerpo) — ideal para producto editorial.
- **Dark mode** real vía `next-themes` + `@custom-variant dark`, tokens en OKLCH para grupos editoriales (`globals.css`).
- **Safe-area / notch** contemplado; touch targets 44px en Header y MobileNav.
- `MobileNav` sólido: `role=dialog`, `aria-modal`, cierre con Escape, bloqueo de scroll, `100dvh`.

---

## 2. Análisis crítico (hallazgos, por prioridad)

| # | Severidad | Problema | Evidencia |
|---|-----------|----------|-----------|
| 1a | 🔴 Crítico | Sin estado activo de navegación | 0 usos de `usePathname`/`aria-current` |
| 1b | 🔴 Crítico | Foco casi inexistente | `focus-visible: 0`, `focus:` solo 5 en toda la app |
| 1c | 🔴 Crítico | Emojis como iconos semánticos | 14 glyphs (`✓ △ ○ ● 🟢 🔴 📋 ⬇ ← →`) |
| 1d | 🔴 Crítico | Sin `prefers-reduced-motion` | 0 ocurrencias; había `animate-bounce`/`pulse`, hover `-translate-y` |
| 2 | 🟠 Alto | Sin estados de carga/error | 0 `loading.tsx`/`error.tsx`/`not-found.tsx`; páginas `force-dynamic` bloqueantes |
| 3 | 🟠 Alto | Paleta de grises inconsistente | **stone (144) + slate (55)** mezclados; hex hardcodeados en charts no theme-aware |
| 4 | 🟡 Alto | Nav primaria sobrecargada | 9 ítems en la barra (recomendado ≤5) |
| 5 | 🟡 Medio | Ancho de contenedor inconsistente | `max-w-3xl/4xl/7xl/2xl` mezclados |
| 6 | 🟡 Bajo | Charts sin a11y de datos | info solo por color; tooltips `title` nativos; sin resumen para lectores |

---

## 3. Cambios implementados

### Quick wins

1. **Estado activo de navegación** — nuevo `components/NavLink.tsx` (client) con `usePathname()` +
   `aria-current="page"` + resalte. Home = match exacto; resto matchea sub-rutas. Cableado en
   `Header.tsx` (desktop) y `MobileNav.tsx` (drawer, con barra de acento izquierda).
2. **Anillo de foco global** — regla `:focus-visible` en `globals.css` para
   `a, button, input, select, textarea, summary, [tabindex]` (stone-500 / stone-400 dark). Cubre toda la app.
3. **Estados de carga/error** — `components/Skeleton.tsx` (reutilizable, `motion-reduce` safe) +
   `app/loading.tsx` (skeleton de grilla), `app/error.tsx` (boundary con **Reintentar** + `digest`),
   `app/not-found.tsx` (404 on-brand).
4. **Unificación de paleta** — 55 `slate-*` → `stone-*` en 11 archivos. Grilla del `AuthorRadarChart`:
   `#e2e8f0` hardcodeado → `currentColor` (`text-stone-200 dark:text-stone-700`) → **ahora adapta a dark mode**.
   `ToneDistributionChart`: tono `otro` slate-400 → stone-500 (distinto de `neutral` stone-400).

### De fondo

5. **Nav 9 → 4 + "Más"** — `lib/nav.ts` separa `PRIMARY_NAV` (Inicio, Preguntar, Análisis, Autores) de
   `SECONDARY_NAV` (Entidades, Sagas, Historial, Fuentes, Suscripciones). Nuevo `components/MoreMenu.tsx`:
   dropdown accesible (`aria-haspopup`/`aria-expanded`, cierra con click-afuera + Escape, chevron rotatorio,
   se resalta en rutas secundarias). El drawer mobile sigue mostrando todo.
6. **Emojis → SVG** — nuevo set `components/icons.tsx` (geometría Lucide, viewBox 24, stroke-width 2).
   Reemplazos en `MarkReadButton`, `ExportMenu`, `BiasScorecard` (🟢/🔴 → `Dot` con `currentColor` + `sr-only`),
   `qa/page.tsx` (coverage badges + thinking dots), y back/forward `←`/`→` en 6 archivos.
   **0 glyphs-como-icono restantes.**
7. **prefers-reduced-motion** — guard global en `globals.css` (`@media (prefers-reduced-motion: reduce)`),
   opt-outs `motion-reduce:animate-none` (skeletons, thinking dots), y `scrollIntoView` de la página QA
   respeta `matchMedia`.
8. **A11y de charts** — `role="img"` + `aria-label` con resumen textual en `AuthorRadarChart` y
   `ToneDistributionChart`. `BiasScorecard` ya era `<table>` real; se le sumaron labels `sr-only`.

### Decisión consciente
- **Anchos de contenedor semánticos (#5):** la mezcla `3xl/4xl/7xl` resultó intencional (lectura angosta
  vs grids anchos). Retrofitear todas las páginas es alto esfuerzo / bajo valor / riesgo de regresión →
  dejado como **follow-up opcional**.

---

## 4. Archivos tocados

**Nuevos:** `web/components/NavLink.tsx`, `MoreMenu.tsx`, `Skeleton.tsx`, `icons.tsx` ·
`web/app/loading.tsx`, `error.tsx`, `not-found.tsx`

**Modificados (24):** `web/lib/nav.ts`, `web/app/globals.css`, `web/components/Header.tsx`, `MobileNav.tsx`,
`ClusterCard.tsx`, `MarkReadButton.tsx`, `ExportMenu.tsx`, `BiasScorecard.tsx`, `CompareColumn.tsx`,
`ToneDistributionChart.tsx`, `AuthorRadarChart.tsx`, `AuthorChip.tsx`, `AuthorArticlesList.tsx`,
`AuthorProfilePanel.tsx`, `AuthorScorecard.tsx`, `AuthorStatsSummary.tsx` · `web/app/qa/page.tsx`,
`compare/page.tsx`, `cluster/[id]/page.tsx`, `saga/[id]/page.tsx`, `entities/[id]/page.tsx`,
`authors/page.tsx`, `authors/[slug]/page.tsx`, `authors/compare/page.tsx`, `authors/compare/clusters/page.tsx`

**Notas de proceso:**
- El swap `slate-`→`stone-` con `sed` tuvo una colisión de substring: `hover:-tran`**`slate-`**`y` →
  `hover:-transtone-y` en `ClusterCard` (Tailwind descarta la clase desconocida sin error de build).
  Detectado revisando el diff y corregido.
- Dos errores de tipo metidos y corregidos: `React.ReactNode` sin namespace importado en `icons.tsx` y `qa/page.tsx`.

---

## 5. Deploy — bloqueo del host (NO es el código)

Secuencia de la sesión:

1. **Push** ✅ — `git push origin main` → `7e46cf2..cccc98f`.
2. **Permisos docker** — usuario `ltaverna` no estaba en grupo `docker`. Tras `usermod -aG docker`,
   funciona vía `sg docker -c "..."` (la membresía nueva aplica recién en login nuevo).
3. **`docker compose build`** ⛔ — falla en todos los `RUN` con
   `failed to start shim: TTRPC connection refused`. Hasta `docker run hello-world` falla.

### Causa raíz (diagnóstico final)

| Señal | Valor |
|-------|-------|
| Kernel corriendo (`uname -r`) | `6.6.4-arch1-1` |
| Módulos en disco (`/usr/lib/modules/`) | **solo `7.0.10-arch1-1`** |
| Uptime | 4 días |
| Server docker | 24.0.7 (CLI 29.5.1) |
| Error real de `dockerd` | `failed to register "bridge" driver: iptables v1.8.13 (nf_tables): Could not fetch rule set generation id: Invalid argument` |

Hace ~4 días un `pacman -Syu` actualizó **kernel (6.6.4 → 7.0.10), iptables/nftables y docker (24 → 29)**
sin reboot. El kernel viejo sigue corriendo pero **sus módulos ya no existen en disco** → netfilter roto →
`dockerd` no puede crear la cadena NAT `DOCKER` → no arranca. **No hay workaround de userspace.**

### Fix (requiere root, en terminal real)

```bash
sudo reboot
```

> El reboot corta esta sesión de Claude Code (corre en la misma máquina, `lucas-mini-pc`).

---

## 6. Próximos pasos (al volver del reboot)

```bash
# 1) Confirmar que el runtime quedó sano
docker run --rm hello-world          # debe imprimir "Hello from Docker!"
sudo systemctl enable --now docker   # solo si el daemon no arrancó solo

# 2) Build + up (desde /opt/brief_noticias)
docker compose build && docker compose up -d
docker compose ps
docker compose logs -f web           # Ctrl-C para salir
```

- Tras el reboot el grupo `docker` queda activo → **ya no hace falta `sudo`/`sg`** en terminales nuevas.
- Compose levanta 3 servicios: `postgres` (pgvector/pg16), `api` (FastAPI, pip), `web` (Next standalone, pnpm).
  Usa `.env` para interpolación y `NEXT_PUBLIC_API_URL` como build-arg del web.
- Reanudando esta conversación, el build + up se puede tirar vía `docker compose ...` (grupo ya activo).

### Follow-ups opcionales (no implementados)
- Anchos de contenedor semánticos unificados (#5).
- Revisar `nginx/` (Dockerfile + nginx.conf sin trackear, **no referenciado por el compose** actual).
