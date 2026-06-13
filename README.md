# Personal Health Observatory

Milestone 1 is a local Withings body-composition pipeline:

```text
Withings API -> Python sync -> TimescaleDB -> Grafana
```

The service imports weight, body-fat percentage, fat mass, fat-free mass, muscle mass,
hydration, and bone mass every six hours. Each raw Withings measure group and every unknown
measurement type are retained alongside normalized values.

## Prerequisites

- Docker with Docker Compose
- A Withings developer application and refresh token
- `uv` for local development

## Withings credentials

Create an application in the Withings Developer Dashboard. Set its callback URL to a local URL
you control, then complete the Withings OAuth 2 authorization-code flow and put the resulting
refresh token in `.env`. The sync service refreshes access tokens automatically and stores rotated
refresh tokens in PostgreSQL.

Do not commit `.env` or real credentials.

## Run locally

```bash
cp .env.example .env
# Fill in WITHINGS_CLIENT_ID, WITHINGS_CLIENT_SECRET, WITHINGS_REFRESH_TOKEN,
# POSTGRES_PASSWORD, and GRAFANA_ADMIN_PASSWORD.
docker compose up --build -d
```

Open Grafana at <http://localhost:3000>. The provisioned **Body Recomposition** dashboard uses the
TimescaleDB datasource automatically.

Useful commands:

```bash
# Follow the scheduled sync
docker compose logs -f sync

# Trigger a one-off sync
docker compose run --rm sync uv run health-observatory sync

# Stop services without deleting data
docker compose down
```

The first sync imports `INITIAL_SYNC_DAYS` of history. Later runs overlap the prior day and upsert,
so corrections made by Withings are retained without duplicate rows.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
docker compose --env-file .env.example config
```

Create a local `.env` only when running the stack. Tests do not require Withings credentials or a
running database.

## Database migrations

Compose runs `alembic upgrade head` before starting the sync service or Grafana. To run migrations
manually:

```bash
docker compose run --rm migrations
```

Milestone 1 intentionally does not include intervals.icu, recovery, workouts, annotations, or
cross-source analytics.
