# AGENTS.md

## Project goal

Build the project described in PRD.md.

## Tech choices

- Python 3.13+
- uv
- PostgreSQL + TimescaleDB
- Grafana
- Docker Compose
- No SQLite
- No cloud deployment

## Development rules

- Work milestone by milestone.
- Start with Withings sync + database + Grafana.
- Do not implement intervals.icu until Withings works.
- Do not commit real secrets.
- Use `.env.example` only.
- Add README instructions for local setup.
- Prefer simple, boring implementation over clever abstractions.

## Validation

Before finishing each task:

- run tests
- run lint/type checks if configured
- verify docker-compose config is valid

## Containers and deployment

Development/runtime target:

- Laptop: Podman
- Homelab: Ubuntu Server + Podman
- Compose format should stay Docker Compose compatible

Use:

- `podman compose up -d`

Avoid:

- Docker-specific features
- privileged containers
- host networking unless necessary
- SELinux-specific volume flags like `:Z`
-
