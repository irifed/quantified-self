# Handoff

## Current status

Milestone 1 is on `main`: Withings sync, TimescaleDB, Grafana, uv project setup, and Podman-compatible Compose.

The current PR adds the intervals.icu milestone:

- intervals.icu sync for wellness records and activities
- `daily_recovery` and `workouts` Timescale hypertables
- source-specific sync commands:
  - `health-observatory sync-withings`
  - `health-observatory sync-intervals`
- Training & Recovery Grafana dashboard
- year-over-year cumulative workout and calorie comparison panels
- HRV import from intervals.icu `hrv` and `hrvSDNN`

The local stack has been validated with real intervals.icu data. Do not commit `.env` or real API tokens.

## How to validate

Run the normal project checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy
podman compose config
```

Run the stack:

```bash
podman compose up --build -d
```

Run only intervals.icu sync:

```bash
podman compose run --rm sync uv run --no-sync health-observatory sync-intervals
```

Open Grafana at <http://localhost:3000> and check the **Training & Recovery** dashboard.

## Implemented dashboards

### Body Recomposition

Provided by Milestone 1 from Withings data.

### Training & Recovery

Added in the intervals.icu milestone. Current panels include:

- Fitness / Fatigue / Form
- HRV (SDNN)
- Resting HR
- Sleep
- Training Load
- Workout Count
- Calories Burned
- Cumulative Workouts by Year
- Cumulative Calories Burned by Year

The cumulative year-over-year panels align all years onto the current calendar year's month/day axis. This allows zooming Grafana to a month, for example May 2026, while comparing May across all imported years.

## Known caveats

- `SPEC.md` contains the product requirements in this checkout, although `AGENTS.md` still refers to `PRD.md`.
- Python in the local virtualenv is currently 3.14, while the project requires Python 3.13+.
- Grafana provisioned dashboard changes may require `podman compose restart grafana` before they appear.
- Withings tokens can rotate. If Withings sync returns auth errors, refresh tokens with `scripts/withings_oauth.py`.
- intervals.icu sync uses `INTERVALS_ATHLETE_ID=0` by default, which means the athlete associated with the API key.

## Recommended next steps

1. Merge the intervals.icu PR into `main`.
2. Add Timescale continuous aggregates for daily, weekly, monthly, and yearly summaries.
3. Add the Period Comparison dashboard from `SPEC.md`.
   - Support presets such as same month last year, current year vs previous year, and custom vs custom.
   - Normalize overlay charts to Day 1, Day 2, Day 3 so arbitrary ranges can be compared.
4. Add `day_annotations` and a simple way to record office days, commute minutes, meeting stress, and notes.
5. Build the Office Day Impact dashboard once annotations exist.

The immediate next implementation milestone should be continuous aggregates plus the Period Comparison dashboard. Manual annotations should follow because the office-day dashboard depends on those annotations.
