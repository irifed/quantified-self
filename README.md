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
value of `WITHINGS_REDIRECT_URI`. Then obtain tokens with the local OAuth helper:

```bash
cp .env.example .env
# Fill in WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET.
uv run python scripts/withings_oauth.py
```

The script opens the Withings authorization page, receives the callback through FastAPI, prints
the access and refresh tokens, and writes both values to `.env`. The sync service refreshes access
tokens automatically and stores rotated refresh tokens in PostgreSQL.

For an ngrok callback, forward the public URL to the local OAuth server and include `/callback` in
the registered URI:

```env
WITHINGS_REDIRECT_URI=https://your-domain.ngrok-free.dev/callback
WITHINGS_OAUTH_HOST=127.0.0.1
WITHINGS_OAUTH_PORT=8000
```

```bash
ngrok http 8000
uv run python scripts/withings_oauth.py
```

Do not commit `.env` or real credentials.

## Run locally

```bash
cp .env.example .env
# Fill in WITHINGS_CLIENT_ID, WITHINGS_CLIENT_SECRET, WITHINGS_REFRESH_TOKEN,
# POSTGRES_PASSWORD, and GRAFANA_ADMIN_PASSWORD.
podman compose up --build -d
```

Open Grafana at <http://localhost:3000>. The provisioned **Body Recomposition** dashboard uses the
TimescaleDB datasource automatically.

Useful commands:

```bash
# Follow the scheduled sync
podman compose logs -f sync

# Trigger a one-off sync
podman compose run --rm sync uv run --no-sync health-observatory sync

# Stop services without deleting data
podman compose down
```

The first sync imports `INITIAL_SYNC_DAYS` of history. Later runs overlap the prior day and upsert,
so corrections made by Withings are retained without duplicate rows.

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

Milestone 1 intentionally does not include intervals.icu, recovery, workouts, annotations, or
cross-source analytics.
