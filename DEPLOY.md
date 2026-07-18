# Deploying the Compliance-Cost Computer (CCC)

This is the production deployment guide for the CCC Docker stack. The stack runs
three services behind a Caddy reverse proxy:

- **caddy** — terminates TLS (automatic HTTPS) and serves everything same-origin.
- **backend** — FastAPI (single worker) on port 5000, reached via `/api/*`.
- **frontend** — Next.js 15 standalone server on port 3000.

Only Caddy is exposed publicly (ports 80/443). The backend and frontend are
reachable only on the internal Docker network.

## Prerequisites

- A host with **Docker** and the **Docker Compose** plugin installed.
- A **public domain name** with a DNS A/AAAA record pointing at the host's
  public IP.
- Inbound **ports 80 and 443** open to the host (Caddy needs both: 80 for the
  ACME HTTP challenge and HTTP→HTTPS redirect, 443 for HTTPS).

## 1. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- `DOMAIN` — the public domain (e.g. `ccc.example.com`). Must match DNS.
- `AUTH_SECRET_KEY` — a long, random secret (e.g. `openssl rand -hex 32`).
- `AUTH_COOKIE_SECURE=true` — required for production HTTPS auth cookies.
- `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD` — the first admin login.
- At least one LLM provider key (`OPENAI_API_KEY`, `DEEPINFRA_API_KEY`,
  and/or `GEMINI_API_KEY`).

`docker-compose.yml` sets `DB_PATH=/data/ccc.db` and
`REGULATIONS_PATH=/data/regulations` for the backend. These point at the
persistent volume and should not normally be changed.

## 2. Build and start

```bash
docker compose up -d --build
```

This builds the backend and frontend images and starts all three services. The
frontend's API base URL is baked in at build time as `/api`
(`NEXT_PUBLIC_API_BASE_URL`), so requests stay same-origin and Caddy strips the
`/api` prefix before forwarding to the backend.

Check status and logs:

```bash
docker compose ps
docker compose logs -f caddy
```

## 3. TLS / HTTPS

TLS is fully automatic. On first start, Caddy contacts Let's Encrypt, completes
the ACME challenge for `DOMAIN`, installs the certificate, and renews it before
expiry. No manual certificate handling is required. Certificates and ACME state
are stored in the `caddy_data` volume, so they survive restarts and rebuilds.

For this to succeed, DNS for `DOMAIN` must already resolve to the host and ports
80/443 must be reachable from the internet.

## Data persistence

All backend state lives on the named Docker volume **`ccc-data`**, mounted at
`/data` inside the backend container:

- `/data/ccc.db` — the SQLite database (sessions, users, results).
- `/data/regulations` — stored regulation files.

This volume persists across `docker compose up`, `down`, and `--build`. It is
only removed if you explicitly run `docker compose down -v`.

Caddy's certificates live on the separate `caddy_data` volume.

### Backup

Back up the `ccc-data` volume regularly. For example, to write a timestamped
tarball to the current directory:

```bash
docker run --rm \
  -v ccc-data:/data:ro \
  -v "$PWD":/backup \
  alpine tar czf /backup/ccc-data-$(date +%F).tar.gz -C /data .
```

Restore into a fresh volume:

```bash
docker run --rm \
  -v ccc-data:/data \
  -v "$PWD":/backup \
  alpine sh -c "cd /data && tar xzf /backup/ccc-data-YYYY-MM-DD.tar.gz"
```

(Stop the backend with `docker compose stop backend` before restoring.)

## Operations

```bash
# Apply config/code changes (rebuild images):
docker compose up -d --build

# Tail logs:
docker compose logs -f backend frontend caddy

# Stop (keeps volumes/data):
docker compose down

# Stop AND delete volumes (DESTROYS data — be careful):
docker compose down -v
```

## Single-replica note

The backend runs as a **single replica with a single Uvicorn worker by design**.

## Build quality gates

The frontend Docker build is optimized for producing the production image. It is
not the quality gate for TypeScript, lint, or Jest checks. Run CI or the local
test commands before deploying:

```bash
python3 -m pytest
npm --prefix frontend test
npm --prefix frontend run lint -- --max-warnings=0
```
The workflow holds in-process session/run-all state and uses a single SQLite
database file, so it must not be horizontally scaled or run with multiple
workers. Do not add `--workers` or a `deploy.replicas` setting for the backend.
