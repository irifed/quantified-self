# Personal Health Observatory

Milestone 1 is a local Withings body-composition pipeline:

```text
Withings API -> Python sync -> TimescaleDB -> Grafana
```

The service imports weight, body-fat percentage, fat mass, fat-free mass, muscle mass,
hydration, and bone mass every six hours. Each raw Withings measure group and every unknown
measurement type are retained alongside normalized values.

## Prerequisites

- Podman with Compose support
- A Withings developer application and refresh token
- `uv` for local development

## Withings credentials

Create an application in the Withings Developer Dashboard and set its callback URL to the exact
value of `WITHINGS_REDIRECT_URI`. Prepare `.env` before starting the OAuth helper:

```bash
cp .env.example .env
# Fill in WITHINGS_CLIENT_ID, WITHINGS_CLIENT_SECRET, and WITHINGS_REDIRECT_URI.
```

The script opens the Withings authorization page, receives the callback through FastAPI, prints
the access and refresh tokens, and writes both values to `.env`. The sync service refreshes access
tokens automatically and stores rotated refresh tokens in PostgreSQL.

For an ngrok callback, use a domain registered with Withings. The redirect URI can be the domain
root or end in `/callback`; it must match the registered URI exactly, including its path:

```env
WITHINGS_REDIRECT_URI=https://your-domain.ngrok-free.dev/callback
WITHINGS_OAUTH_HOST=127.0.0.1
WITHINGS_OAUTH_PORT=8000
```

```bash
# Terminal 1: keep this running until authorization completes.
ngrok http 8000 --url https://your-domain.ngrok-free.dev

# Terminal 2: run after ngrok reports the tunnel is online.
uv run python scripts/withings_oauth.py
```

The `--url` value must be the domain in `WITHINGS_REDIRECT_URI` (without a trailing `/callback` path).
If the browser shows `ERR_NGROK_3200`, the tunnel is offline. Start or reconnect ngrok, then use
the authorization URL printed by the still-running OAuth helper to authorize again. If the helper
has exited, rerun it. Stop ngrok after the helper reports that tokens were saved.

Do not commit `.env` or real credentials.

## Run locally

```bash
cp .env.example .env
# Fill in WITHINGS_CLIENT_ID, WITHINGS_CLIENT_SECRET, WITHINGS_REFRESH_TOKEN,
# POSTGRES_PASSWORD, and GRAFANA_ADMIN_PASSWORD.
podman compose up --build -d
```

PostgreSQL and Grafana store their state in `./data/postgres` and `./data/grafana` on the host.
The `data/` directory is ignored by Git. On macOS, keep this project under a directory shared
with the Podman machine (the default machine shares the user's home directory). These bind mounts
survive replacing the Podman machine, but they are not backups. For a consistent filesystem backup,
stop the stack before copying `data/`; for a live PostgreSQL backup, use `pg_dump`.
Do not use `podman compose down -v` when using a Compose file with named volumes from an older
installation unless you have confirmed those volumes are no longer needed.

`DATABASE_URL` is optional. Compose builds the connection URL from the PostgreSQL fields safely,
including when the password contains URL-special characters.

Open Grafana at <http://localhost:3000>. The provisioned **Body Recomposition** dashboard uses the
TimescaleDB datasource automatically.

Useful commands:

```bash
# Follow the scheduled sync
podman compose logs -f sync

# Trigger a one-off sync
podman compose run --rm sync uv run --no-sync health-observatory sync

# Trigger only intervals.icu sync
podman compose run --rm sync uv run --no-sync health-observatory sync-intervals

# Trigger only Withings sync
podman compose run --rm sync uv run --no-sync health-observatory sync-withings

# Stop services without deleting data
podman compose down
```

The first sync imports `INITIAL_SYNC_DAYS` of history. Later runs overlap the prior day and upsert,
so corrections made by Withings are retained without duplicate rows.

## Rebuild after replacing a Podman machine

Keep your existing `.env`. Before the first sync into an empty database, set `INITIAL_SYNC_DAYS`
and `INTERVALS_INITIAL_SYNC_DAYS` large enough to cover your history. The defaults are 3650 days
(about ten years). Then run:

```bash
podman compose up --build -d timescaledb migrations grafana
podman compose run --rm sync uv run --no-sync health-observatory sync-intervals
podman compose run --rm sync uv run --no-sync health-observatory sync-withings
podman compose up -d sync
podman compose ps
```

The intervals.icu API key in `.env` can be reused. Withings rotates refresh tokens and stores the
latest token in PostgreSQL; after losing the old database, the token in `.env` may no longer work.
If the Withings sync returns an authentication error, run `uv run python scripts/withings_oauth.py`
to obtain fresh tokens, then retry `sync-withings`.

Open <http://localhost:3000> and check the **Body Recomposition** and **Training & Recovery**
dashboards. Back up `data/` while the stack is stopped, or use a PostgreSQL dump plus a backup of
`data/grafana` while Grafana is stopped. Keep an additional copy outside this Mac.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
podman compose --env-file .env.example config
```

Create a local `.env` only when running the stack. Tests do not require Withings credentials or a
running database.

## Database migrations

Compose runs `alembic upgrade head` before starting the sync service or Grafana. To run migrations
manually:

```bash
podman compose run --rm migrations
```

Manual annotations, office-day analysis, period comparison, and cross-source analytics are not
implemented yet.

## intervals.icu Sync

Generate an API key in
intervals.icu **Settings → Developer Settings**, then add it to `.env`:

```env
INTERVALS_API_KEY=your_api_key
INTERVALS_ATHLETE_ID=0
```

`0` selects the athlete associated with the API key. The sync imports wellness records into
`daily_recovery` and activities into `workouts`, then Grafana provisions the **Training & Recovery**
dashboard automatically.
