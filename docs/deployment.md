# Deployment guide

Cómo llevar `noticias` a un host fuera de tu PC (Raspberry Pi, VPS, otro server) con Cloudflare Tunnel para que tengas URL pública sin abrir puertos.

## Arquitectura objetivo

```
   Telegram (celu) ────┐
                       │
   Browser (cualquiera)─┼──> https://noticias.tudominio.com
                       │           │
                       │           │ (Cloudflare Tunnel)
                       │           ▼
                       │   ┌─────────────────────────┐
                       │   │  Tu host (Raspberry Pi) │
                       │   │  ┌──────┐  ┌──────┐    │
                       └──>│  │ web  │  │ api  │    │
                           │  │ :3000│  │ :8000│    │
                           │  └──────┘  └──────┘    │
                           │  ┌─────────────┐        │
                           │  │ postgres    │        │
                           │  │ +pgvector   │        │
                           │  └─────────────┘        │
                           └─────────────────────────┘
```

Ningún puerto expuesto a internet directamente. El tunnel de Cloudflare es saliente: tu host se conecta a Cloudflare y este enruta tráfico entrante hacia tus servicios locales.

## Requisitos en el host

- Linux (Raspberry Pi OS / Debian / Ubuntu)
- Docker + Docker Compose v2 (`apt install docker.io docker-compose-v2` o el script oficial)
- 2GB RAM mínimo (4GB recomendado para Postgres + embeddings batch)
- ~5GB disco para Postgres + imágenes Docker
- Cuenta de Cloudflare (gratis) con un dominio agregado (puede ser uno comprado en Namecheap, redirigido a Cloudflare DNS)

## Paso 1 — Preparar el host

```bash
# 1. Clonar el repo
git clone <tu-repo-noticias> /opt/noticias
cd /opt/noticias

# 2. Crear .env de producción
cp .env.example .env
nano .env
```

Editá `.env` con valores de producción:

```env
# OpenAI (rotar si pasaste el token por chat)
OPENAI_API_KEY=sk-tu-key-real

# Database — usá password fuerte para producción
POSTGRES_USER=noticias
POSTGRES_PASSWORD=<algo-aleatorio-largo>
POSTGRES_DB=noticias
DATABASE_URL=postgresql+psycopg://noticias:<password>@postgres:5432/noticias

# API
API_PORT=8000
LOG_LEVEL=INFO

# Pipeline
CRON_HOUR=7
CRON_HOURS=7,13,20         # múltiples corridas por día
TOP_N_CLUSTERS=20
SIMILARITY_THRESHOLD=0.70
MERGE_THRESHOLD=0.85
MERGE_WINDOW_HOURS=72
SAGA_THRESHOLD=0.78
SAGA_WINDOW_HOURS=168

# Frontend — URL pública del Cloudflare Tunnel
WEB_PORT=3000
NEXT_PUBLIC_API_URL=https://noticias.tudominio.com    # mismo dominio que el frontend
INTERNAL_API_URL=http://api:8000
PUBLIC_BASE_URL=https://noticias.tudominio.com         # links del digest apuntan acá

# Telegram
TELEGRAM_BOT_TOKEN=<token-completo>
TELEGRAM_CHAT_ID=<tu-chat-id>
ENABLE_TELEGRAM=true
TELEGRAM_BOT_MODE=webhook                              # ahora sí webhook, tenemos URL pública
TELEGRAM_WEBHOOK_SECRET=<generar-con-openssl-rand>
TELEGRAM_ALLOWED_CHATS=<tu-chat-id>                    # opcional CSV; default = solo TELEGRAM_CHAT_ID
```

Generá el `TELEGRAM_WEBHOOK_SECRET`:

```bash
openssl rand -hex 32
```

## Paso 2 — Cloudflare Tunnel

### 2.1 Instalar `cloudflared` en el host

Raspberry Pi (ARM):

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

Otros (x86_64):

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### 2.2 Autenticar y crear tunnel

```bash
cloudflared tunnel login                      # abre browser, elegís tu dominio
cloudflared tunnel create noticias            # crea tunnel, devuelve un UUID
```

Guardá el UUID que imprime (también queda en `~/.cloudflared/<uuid>.json`).

### 2.3 Configurar tunnel

Crear `~/.cloudflared/config.yml`:

```yaml
tunnel: <UUID-que-cloudflared-te-dio>
credentials-file: /root/.cloudflared/<UUID>.json

ingress:
  - hostname: noticias.tudominio.com
    service: http://localhost:3000
  # Si querés exponer la API directo (ej: para webhooks de Telegram):
  - hostname: api.noticias.tudominio.com
    service: http://localhost:8000
  - service: http_status:404
```

### 2.4 Crear DNS record

```bash
cloudflared tunnel route dns noticias noticias.tudominio.com
cloudflared tunnel route dns noticias api.noticias.tudominio.com
```

### 2.5 Levantar tunnel como servicio systemd

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

Verificá que `https://noticias.tudominio.com` redirija a tu servicio (aunque tu Docker compose todavía no esté arriba).

## Paso 3 — Ajuste de NEXT_PUBLIC_API_URL

`NEXT_PUBLIC_API_URL` se "hornea" al bundle de Next.js durante `pnpm build`. Necesitás que el build use la URL pública.

El `Dockerfile` actual de `web/` no pasa esta var al builder. Hay dos formas:

**A. Pasar como build-arg (recomendado):**

Editar `web/Dockerfile` para aceptar `NEXT_PUBLIC_API_URL` como ARG y exportarlo como ENV antes del build:

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm build
```

Y en `docker-compose.yml`, pasar el arg:

```yaml
web:
  build:
    context: ./web
    args:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
```

**B. Usar runtime fetch (más complejo):** mover toda la API a una sola URL relativa via Next.js proxy routes, evitando la necesidad de variable build-time. Más cambios.

Recomendado A. Así, `NEXT_PUBLIC_API_URL=https://noticias.tudominio.com/api` (si el frontend y la API comparten dominio via routing) o `https://api.noticias.tudominio.com` (si están separadas).

## Paso 4 — Levantar todo

```bash
cd /opt/noticias
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Sembrar fuentes (solo la primera vez):

```bash
docker compose exec api python -c "
import asyncio
from noticias_api.db.session import async_session_factory
from noticias_api.db.seed import seed_sources
async def main():
    async with async_session_factory() as s:
        print(await seed_sources(s))
asyncio.run(main())
"
```

Visitar `https://noticias.tudominio.com` — debería renderizar.

## Paso 5 — Configurar webhook de Telegram

Ahora que tenés URL pública, registrá el webhook (esto reemplaza el polling):

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url":"https://api.noticias.tudominio.com/telegram/webhook"}' \
  https://api.noticias.tudominio.com/telegram/setup-webhook
```

Verificar:

```bash
curl https://api.noticias.tudominio.com/telegram/info
```

Tiene que mostrar `webhook_info.url` con tu URL.

A partir de acá: cualquier mensaje que mandes al bot pasa por el webhook (fast, sin polling overhead).

Si querés volver a polling temporalmente: `curl -X POST .../telegram/clear-webhook` y cambiá `TELEGRAM_BOT_MODE=polling` en `.env`, restart api.

## Paso 6 — Backups automáticos

El script `scripts/backup.sh` ya está. Agregar al crontab del host:

```bash
sudo crontab -e
```

```cron
0 4 * * * cd /opt/noticias && ./scripts/backup.sh >> /var/log/noticias-backup.log 2>&1
```

Backups van a `./backups/` con rotación de 7 días.

Para restaurar:

```bash
docker compose exec -T postgres pg_restore -U noticias -d noticias < backups/noticias-XXXX.dump
```

## Paso 7 — Auto-arranque al reboot

Docker Compose con `restart: unless-stopped` (ya está en el compose) levanta los containers al reboot.

`cloudflared` instalado como systemd service también arranca solo.

Verificar después de un reboot:

```bash
docker compose ps          # los 3 containers running
systemctl status cloudflared
curl https://noticias.tudominio.com/   # 200 OK
```

## Paso 8 — Updates

```bash
cd /opt/noticias
git pull
docker compose up -d --build
docker compose exec api alembic upgrade head    # si hay migraciones nuevas
```

## Troubleshooting

### El bot no responde a mensajes
1. `curl https://api.noticias.tudominio.com/telegram/info` — `webhook_info.last_error_date` debería ser 0 o ausente. Si hay error, lo dice ahí.
2. `docker compose logs api | grep -i telegram` — busca errores de procesamiento.
3. `TELEGRAM_ALLOWED_CHATS` o `TELEGRAM_CHAT_ID` filtra: si tu chat_id no coincide, el bot ignora silenciosamente.

### Cloudflare Tunnel "no se conecta"
- `journalctl -u cloudflared -f` — ver logs en vivo
- Verificar que tu DNS resuelve (`dig noticias.tudominio.com`) — si Cloudflare no creó el CNAME, hacelo manualmente desde su dashboard apuntando a `<UUID>.cfargotunnel.com`

### El digest manda links viejos
- `PUBLIC_BASE_URL` en `.env` no se actualizó. Cambialo, restart api.
- Mensajes ya enviados no se modifican (entendible).

### "QA failed: 504" desde el browser
- El tunnel de Cloudflare tiene timeout default ~100s. Las preguntas RAG normalmente terminan en 5-15s. Si tardan más, hay otro problema (OpenAI lento, embedding query lento). Logs del api van a tener el detalle.

### El pipeline cron no corre
- Timezone del container es `America/Argentina/Buenos_Aires` (hardcoded en `scheduler.py`). Si tu host tiene otro timezone, los logs van a marcar UTC pero el scheduler usa AR.
- `docker compose logs api | grep -i cron` después de un día.

## Hardening recomendado

- **HTTPS-only:** Cloudflare Tunnel ya hace HTTPS automáticamente.
- **Rate limit:** Cloudflare tiene rate-limit gratis hasta cierto threshold. Activalo en su dashboard si planeás exponer públicamente.
- **API authentication:** actualmente la API no tiene auth. Para uso personal con tunnel + chat allowlist en Telegram alcanza, pero si vas a abrirlo a más gente, considerá HTTP basic auth via Cloudflare Access (gratis) o un reverse proxy con auth.
- **Postgres password rotation:** rotar cada N meses. Actualizar `POSTGRES_PASSWORD` y `DATABASE_URL` en `.env`, después `docker compose down` + `up`. Postgres preserva el password viejo si los datos no se borran — hay que ALTER USER manualmente o recrear.

## Recursos típicos en RPi 4 (4GB)

- Postgres: ~300MB RAM
- API: ~150MB RAM (Python)
- Web: ~100MB RAM (Next.js standalone)
- Total ~600MB en idle, ~1-1.5GB durante un pipeline run
- CPU: spikes durante embeddings + análisis (~30 segundos), idle el resto
- OpenAI API: ~$5-15/mes para uso personal con varios runs/día

## Migración desde tu PC actual

Si querés llevar la DB con análisis ya generados:

```bash
# En tu PC actual:
./scripts/backup.sh
scp backups/noticias-XXXX.dump pi@raspi:/opt/noticias/backups/

# En el RPi:
cd /opt/noticias
docker compose up postgres -d
docker compose exec postgres psql -U noticias -d noticias -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose exec api alembic upgrade head
docker compose exec -T postgres pg_restore -U noticias -d noticias --clean --if-exists < backups/noticias-XXXX.dump
docker compose up -d
```

---

Si surge algo raro al deployar, revisá `docker compose logs <servicio>` primero. La mayoría de problemas son env vars mal puestas o el tunnel no enrutando.
