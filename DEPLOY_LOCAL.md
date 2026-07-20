# Running CCC locally

This guide covers running the Compliance-Cost Computer (CCC) **on your own
machine**. For internet-facing production deployment with automatic TLS, see
[DEPLOY.md](DEPLOY.md) instead.

The production stack ([DEPLOY.md](DEPLOY.md)) assumes a public domain so Caddy can
obtain a real TLS certificate. Locally there is no public domain, so we point
Caddy at `localhost`. Two small `.env` changes are all that differ.

---

## Option A — Docker stack on `localhost` (recommended)

Runs the real production stack (Caddy + frontend + backend, same-origin) on your
machine.

### Prerequisites
- **Docker** and the **Docker Compose** plugin installed and running
  (e.g. Docker Desktop).
- Host **port 80** free (see "Port 80 in use" below if it isn't).

### 1. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and set the following for a local run:

```dotenv
# Plain HTTP on localhost (no public certificate, no browser warning).
DOMAIN=http://localhost
# The auth cookie must be allowed over HTTP when running without TLS.
AUTH_COOKIE_SECURE=false

# A long random secret for signing auth tokens (generate one, see below).
AUTH_SECRET_KEY=replace-me

# First admin account, created automatically on first start.
ADMIN_BOOTSTRAP_EMAIL=admin@example.com
ADMIN_BOOTSTRAP_PASSWORD=choose-a-password-8+chars

# LLM provider keys are optional here — you can also paste them in the UI.
OPENAI_API_KEY=
DEEPINFRA_API_KEY=
GEMINI_API_KEY=
```

Generate a secret for `AUTH_SECRET_KEY`:

```bash
openssl rand -hex 32
```

`docker-compose.yml` sets `DB_PATH=/data/ccc.db`,
`REGULATIONS_PATH=/data/regulations`, and `NEXT_PUBLIC_API_BASE_URL=/api` for the
Docker services. Leave those Docker defaults unchanged.

### 2. Build and start

```bash
docker compose up -d --build
```

The first build takes a few minutes (pip + npm). Fonts are vendored
(`@fontsource`), so the build needs **no** Google Fonts network access.

### 3. Open the app

Visit **http://localhost** and log in with the `ADMIN_BOOTSTRAP_EMAIL` /
`ADMIN_BOOTSTRAP_PASSWORD` you set. As an admin you can create more users via the
**Benutzerverwaltung** button in the header (there is no public self-registration).

### 4. Operate

```bash
docker compose ps                                  # service status
docker compose logs -f backend frontend caddy      # tail logs
docker compose down                                # stop (keeps data)
docker compose down -v                             # stop AND wipe the DB volume
```

Data (SQLite DB, regulations) persists in the `ccc-data` Docker volume across
restarts; it is only deleted by `docker compose down -v`.

### Variant: HTTPS on `localhost`

To exercise the Secure-cookie / HTTPS path locally, set instead:

```dotenv
DOMAIN=localhost
AUTH_COOKIE_SECURE=true
```

Then open **https://localhost**. Caddy serves it with its own internal CA, so the
browser shows a one-time certificate warning. To trust Caddy's local root CA and
remove the warning:

```bash
docker compose exec caddy caddy trust
```

### Port 80 in use

If something else already uses port 80, remap Caddy's published port in
`docker-compose.yml`:

```yaml
  caddy:
    ports:
      - "8080:80"     # was "80:80"
      - "443:443"
```

Then browse **http://localhost:8080**.

---

## Option B — No Docker (fast iteration)

Run the backend and frontend directly in two terminals. This uses the env-based
CORS defaults (which already allow `http://localhost:3000`) rather than the
same-origin Caddy proxy.

### Backend (terminal 1)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AUTH_SECRET_KEY="$(openssl rand -hex 32)"
export AUTH_COOKIE_SECURE=false
export ADMIN_BOOTSTRAP_EMAIL=admin@example.com
export ADMIN_BOOTSTRAP_PASSWORD=choose-a-password-8+chars

uvicorn backend.main:app --reload --port 5000
```

(These can also live in a `.env` file at the repo root, which the backend reads.)

### Frontend (terminal 2)

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Then open **http://localhost:3000** and log in with the bootstrap admin. The
frontend talks to the backend at `http://localhost:5000` by default
(`NEXT_PUBLIC_API_BASE_URL` is unset in dev).

---

## Tests

```bash
# Backend
python3 -m pytest

# Frontend
npm --prefix frontend test
npm --prefix frontend run lint -- --max-warnings=0
```
