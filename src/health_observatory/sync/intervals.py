from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from health_observatory.config import Settings
from health_observatory.models import DailyRecovery, SyncState, Workout

BASE_URL = "https://intervals.icu/api/v1"
SOURCE = "intervals_icu"


class IntervalsApiError(RuntimeError):
    pass


def parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def date_timestamp(value: str) -> datetime:
    return datetime.combine(parse_date(value), time.min, tzinfo=UTC)


def number(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    return float(value)


def seconds_to_minutes(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) / 60.0


def seconds_to_hours(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) / 3600.0


def normalize_wellness(record: dict[str, Any]) -> dict[str, Any]:
    fitness = number(record, "ctl")
    fatigue = number(record, "atl")
    hrv = number(record, "hrv")
    return {
        "timestamp": date_timestamp(str(record["id"])),
        "resting_hr": number(record, "restingHR"),
        "hrv": hrv if hrv is not None else number(record, "hrvSDNN"),
        "sleep_hours": seconds_to_hours(record.get("sleepSecs")),
        "sleep_score": number(record, "sleepScore"),
        "fitness": fitness,
        "fatigue": fatigue,
        "form": None if fitness is None or fatigue is None else fitness - fatigue,
        "source": SOURCE,
        "raw_payload": record,
    }


def normalize_activity(activity: dict[str, Any]) -> dict[str, Any]:
    timestamp_value = activity.get("start_date") or activity.get("start_date_local")
    if not timestamp_value:
        raise IntervalsApiError(f"Activity {activity.get('id')} did not include a start date")
    duration = activity.get("moving_time") or activity.get("elapsed_time")
    return {
        "timestamp": parse_datetime(str(timestamp_value)),
        "intervals_activity_id": str(activity["id"]),
        "activity_type": activity.get("type") or activity.get("sub_type"),
        "duration_minutes": seconds_to_minutes(duration),
        "training_load": number(activity, "icu_training_load"),
        "avg_hr": number(activity, "average_heartrate"),
        "max_hr": number(activity, "max_heartrate"),
        "calories": number(activity, "calories"),
        "source": SOURCE,
        "raw_payload": activity,
    }


class IntervalsClient:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.auth = httpx.BasicAuth("API_KEY", settings.intervals_api_key.get_secret_value())
        self.headers = {"User-Agent": "Mozilla/5.0 health-observatory/0.1"}
        self.http = http_client or httpx.Client(timeout=30.0)

    def __enter__(self) -> "IntervalsClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.http.close()

    def list_wellness(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        response = self.http.get(
            f"{BASE_URL}/athlete/{self.settings.intervals_athlete_id}/wellness",
            auth=self.auth,
            headers=self.headers,
            params={
                "oldest": oldest.isoformat(),
                "newest": newest.isoformat(),
                "fields": [
                    "id",
                    "ctl",
                    "atl",
                    "restingHR",
                    "hrv",
                    "hrvSDNN",
                    "sleepSecs",
                    "sleepScore",
                ],
            },
        )
        return checked_json_list(response)

    def list_activities(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        response = self.http.get(
            f"{BASE_URL}/athlete/{self.settings.intervals_athlete_id}/activities",
            auth=self.auth,
            headers=self.headers,
            params={
                "oldest": oldest.isoformat(),
                "newest": newest.isoformat(),
                "fields": [
                    "id",
                    "start_date",
                    "start_date_local",
                    "type",
                    "moving_time",
                    "elapsed_time",
                    "icu_training_load",
                    "average_heartrate",
                    "max_heartrate",
                    "calories",
                ],
            },
        )
        return checked_json_list(response)


def checked_json_list(response: httpx.Response) -> list[dict[str, Any]]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise IntervalsApiError("Intervals.icu response was not a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def sync_intervals(session: Session, settings: Settings, client: IntervalsClient) -> dict[str, int]:
    if not settings.intervals_configured:
        return {"daily_recovery": 0, "workouts": 0}

    state = session.get(SyncState, SOURCE)
    today = datetime.now(UTC).date()
    if state and state.last_sync:
        oldest = (state.last_sync - timedelta(days=7)).date()
    else:
        oldest = today - timedelta(days=settings.intervals_initial_sync_days)

    wellness_rows = [normalize_wellness(item) for item in client.list_wellness(oldest, today)]
    activity_rows = [normalize_activity(item) for item in client.list_activities(oldest, today)]

    if wellness_rows:
        statement = insert(DailyRecovery).values(wellness_rows)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[DailyRecovery.timestamp],
            set_={
                "resting_hr": excluded.resting_hr,
                "hrv": excluded.hrv,
                "sleep_hours": excluded.sleep_hours,
                "sleep_score": excluded.sleep_score,
                "fitness": excluded.fitness,
                "fatigue": excluded.fatigue,
                "form": excluded.form,
                "raw_payload": excluded.raw_payload,
            },
        )
        session.execute(statement)

    if activity_rows:
        statement = insert(Workout).values(activity_rows)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[Workout.timestamp, Workout.intervals_activity_id],
            set_={
                "activity_type": excluded.activity_type,
                "duration_minutes": excluded.duration_minutes,
                "training_load": excluded.training_load,
                "avg_hr": excluded.avg_hr,
                "max_hr": excluded.max_hr,
                "calories": excluded.calories,
                "raw_payload": excluded.raw_payload,
            },
        )
        session.execute(statement)

    if state is None:
        state = SyncState(source=SOURCE)
        session.add(state)
    state.last_sync = datetime.now(UTC)
    state.cursor = {"oldest": oldest.isoformat(), "newest": today.isoformat()}
    return {"daily_recovery": len(wellness_rows), "workouts": len(activity_rows)}
