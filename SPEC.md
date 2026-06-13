# PRD: Personal Health Observatory

## Overview

Personal Health Observatory is a self-hosted health analytics platform that aggregates health, fitness, recovery, sleep, and body-composition data from existing tools and devices.

The platform is designed for long-term trend analysis and decision support, not daily readiness scoring.

Primary objectives:

1. Track healthy aging metrics over years.
2. Monitor body recomposition (fat loss vs muscle gain).
3. Understand relationships between sleep, stress, training, and recovery.
4. Quantify the impact of office days and commuting.
5. Compare arbitrary time periods (month-over-month, year-over-year, custom ranges).
6. Automate data collection as much as possible.

The platform is intended to complement existing tools (Apple Watch, AutoSleep, HealthFit, intervals.icu, Withings) rather than replace them.

---

# Existing Ecosystem

## Already Available

Hardware:

- Apple Watch
- Polar H10
- Withings Scale

Applications:

- AutoSleep
- HealthFit
- intervals.icu

Existing flow:

Apple Watch → HealthFit → intervals.icu

Current gap:

Withings body-composition metrics are not fully available in intervals.icu.

Especially:

- muscle mass
- fat mass
- fat-free mass
- hydration
- bone mass

---

# Product Vision

Create a personal observability platform similar to engineering observability systems.

Not:

"What is my readiness score today?"

Instead:

- Why is sleep worse before office days?
- Is muscle mass increasing over 6 months?
- Does training consistency improve body composition?
- Is recovery worse after long commute days?
- Am I healthier this year than last year?

---

# Architecture

```text
                    Withings API
                         │
                         ▼

                 Sync Service (Python)

                         │

 intervals.icu API ──────┼────── Manual Tags

                         │

                         ▼

                PostgreSQL + TimescaleDB

                         │

                         ▼

                      Grafana
```

---

# Technology Stack

## Backend

Python 3.13+

Package management:

- uv

Libraries:

- SQLAlchemy
- Alembic
- APScheduler
- httpx
- pydantic
- pandas

## Database

PostgreSQL

Extension:

- TimescaleDB

Reason:

- time-series support
- rolling aggregates
- Grafana integration
- flexible analytics
- future-proofing

## Visualization

Grafana

## Deployment

Docker Compose

Single-node homelab deployment.

---

# Repository Structure

```text
health-observatory/

├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── .env.example
├── README.md

├── grafana/
│   ├── dashboards/
│   ├── datasources/
│   └── provisioning/

├── migrations/

├── src/
│   └── health_observatory/
│       ├── config.py
│       ├── db.py
│       ├── scheduler.py
│       ├── main.py
│       │
│       ├── models/
│       ├── sync/
│       ├── analytics/
│       ├── services/
│       └── api/

└── tests/
```

---

# Environment Variables

```env
POSTGRES_DB=health
POSTGRES_USER=health
POSTGRES_PASSWORD=change_me

WITHINGS_CLIENT_ID=
WITHINGS_CLIENT_SECRET=
WITHINGS_REFRESH_TOKEN=

INTERVALS_API_KEY=
INTERVALS_ATHLETE_ID=

TZ=Europe/Amsterdam

SYNC_INTERVAL_HOURS=6
```

---

# Data Sources

# Source 1 — Withings

## Purpose

Body composition source of truth.

## Sync Frequency

Every 6 hours.

## Metrics

Weight

Fat ratio %

Fat mass

Fat-free mass

Muscle mass

Hydration

Bone mass

Visceral fat if available

## Requirements

Store:

- raw payload
- normalized measurements

Unknown metric types must be preserved.

Never discard data.

---

# Source 2 — intervals.icu

## Purpose

Training and recovery source of truth.

## Sync Frequency

Every 6 hours.

## Metrics

Workouts

Training load

Fitness

Fatigue

Form

HRV

Resting HR

Sleep metrics (if available)

Activity summaries

Workout history

No direct Apple Health integration should be built.

HealthFit + intervals.icu already solve that problem.

---

# Source 3 — Manual Annotations

Required for contextual analysis.

Fields:

date

office_day

commute_minutes

important_meeting

stress_level

notes

---

# Database Design

## hypertable: body_composition

Columns:

timestamp

weight_kg

fat_ratio_pct

fat_mass_kg

fat_free_mass_kg

muscle_mass_kg

hydration_kg

bone_mass_kg

source

Timescale hypertable.

---

## hypertable: daily_recovery

timestamp

resting_hr

hrv

sleep_hours

sleep_score

fitness

fatigue

form

source

Timescale hypertable.

---

## hypertable: workouts

timestamp

activity_type

duration_minutes

training_load

avg_hr

max_hr

calories

source

Timescale hypertable.

---

## table: day_annotations

date

office_day

commute_minutes

important_meeting

stress_level

notes

updated_at

---

## table: sync_state

source

last_sync

cursor

updated_at

---

# Continuous Aggregates

Create Timescale continuous aggregates.

## Daily Aggregate

Store:

daily averages

daily maxima

daily minima

---

## Weekly Aggregate

Store:

weekly body composition

weekly recovery

weekly training

---

## Monthly Aggregate

Store:

monthly averages

monthly deltas

---

## Yearly Aggregate

Store:

year-over-year statistics

---

# Grafana Dashboards

# Dashboard 1 — Body Recomposition

Goal:

Am I losing fat while maintaining or gaining muscle?

Panels:

Weight

Body Fat %

Fat Mass

Fat-Free Mass

Muscle Mass

Lean-to-Fat Ratio

Display:

raw values

7-day moving average

28-day moving average

monthly average

---

# Dashboard 2 — Training & Recovery

Goal:

Is training producing positive adaptation?

Panels:

Fitness

Fatigue

Form

HRV

Resting HR

Sleep

Workout Count

Training Load

---

# Dashboard 3 — Office Day Impact

Goal:

Quantify the physiological impact of office attendance.

Comparisons:

Office Days

vs

Home Days

Metrics:

Sleep

HRV

Resting HR

Fitness

Fatigue

Form

Additional comparisons:

Important meeting days

Long commute days

Short commute days

---

# Dashboard 4 — Healthy Aging

Goal:

Track long-term health trajectory.

Metrics:

Resting HR

HRV

VO₂max (if available)

Weight

Fat %

Muscle Mass

Training Consistency

Sleep

Time horizons:

1 year

2 years

5 years

---

# Dashboard 5 — Period Comparison

Most important dashboard.

Goal:

Compare any two time periods.

---

## User Inputs

Range A Start

Range A End

Range B Start

Range B End

Metric

---

## Supported Metrics

Weight

Fat %

Fat Mass

Muscle Mass

Fat-Free Mass

Sleep

HRV

Resting HR

Fitness

Fatigue

Form

Training Load

---

## Output

### Summary Cards

Average A

Average B

Absolute Delta

Percentage Delta

Example:

Muscle Mass

Range A: 42.1 kg

Range B: 43.0 kg

Delta: +0.9 kg

+2.1%

### Overlay Chart

Normalize both ranges into:

Day 1

Day 2

Day 3

...

Allow:

May vs June

This year vs last year

Current quarter vs previous quarter

Custom vs custom

---

## Presets

This Month vs Last Month

Last Full Month vs Previous Month

Last 90 Days vs Previous 90 Days

Same Month Last Year

Current Year vs Previous Year

Custom vs Custom

---

# Analytics

## Body Composition

Calculate:

Lean-to-Fat Ratio

Muscle Mass %

Fat Mass %

Monthly Muscle Change

Monthly Fat Change

---

## Office-Day Analysis

Calculate:

Average sleep before office day

Average sleep before home day

HRV difference

Resting HR difference

Recovery difference

---

## Training Correlations

Calculate:

Training Load vs Muscle Mass

Training Frequency vs Body Fat

Sleep vs HRV

Sleep vs Resting HR

---

# Automation Requirements

No manual exports after initial setup.

System should:

- sync Withings automatically
- sync intervals.icu automatically
- update Timescale aggregates automatically
- refresh Grafana automatically

Scheduled every 6 hours.

---

# Future Enhancements

Not MVP.

Potential additions:

- Google Calendar integration
- Automatic office-day detection
- AI-generated monthly report
- Email summary
- Protein tracking
- Nutrition imports
- Correlation explorer
- Alerting

---

# Success Criteria

The project is successful when:

1. No manual data collection is required.
2. Muscle mass appears in Grafana automatically.
3. Training and body-composition data are visible in one place.
4. Any two periods can be compared.
5. Office-day impact can be quantified.
6. Month-over-month and year-over-year trends are available.
7. Everything runs locally on the homelab using Docker Compose.
8. Historical data accumulates indefinitely.
