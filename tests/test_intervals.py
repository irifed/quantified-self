from datetime import UTC, date, datetime

import httpx
from pydantic import SecretStr

from health_observatory.config import Settings
from health_observatory.sync.intervals import (
    BASE_URL,
    IntervalsClient,
    normalize_activity,
    normalize_wellness,
)


def settings() -> Settings:
    return Settings(intervals_api_key=SecretStr("api-key"), intervals_athlete_id="0")


def test_normalize_wellness_maps_recovery_fields() -> None:
    result = normalize_wellness(
        {
            "id": "2026-07-12",
            "restingHR": 48,
            "hrv": 72.5,
            "sleepSecs": 28800,
            "sleepScore": 86,
            "ctl": 54.2,
            "atl": 61.7,
        }
    )

    assert result["timestamp"] == datetime(2026, 7, 12, tzinfo=UTC)
    assert result["resting_hr"] == 48
    assert result["hrv"] == 72.5
    assert result["sleep_hours"] == 8
    assert result["sleep_score"] == 86
    assert result["fitness"] == 54.2
    assert result["fatigue"] == 61.7
    assert result["form"] == -7.5
    assert result["source"] == "intervals_icu"


def test_normalize_wellness_uses_hrv_sdnn_when_rmssd_is_absent() -> None:
    result = normalize_wellness({"id": "2026-07-12", "hrvSDNN": 41.5})

    assert result["hrv"] == 41.5


def test_normalize_activity_maps_workout_fields() -> None:
    result = normalize_activity(
        {
            "id": "activity-1",
            "start_date": "2026-07-12T05:30:00Z",
            "type": "Ride",
            "moving_time": 3600,
            "icu_training_load": 72,
            "average_heartrate": 134,
            "max_heartrate": 171,
            "calories": 640,
        }
    )

    assert result["timestamp"] == datetime(2026, 7, 12, 5, 30, tzinfo=UTC)
    assert result["intervals_activity_id"] == "activity-1"
    assert result["activity_type"] == "Ride"
    assert result["duration_minutes"] == 60
    assert result["training_load"] == 72
    assert result["avg_hr"] == 134
    assert result["max_hr"] == 171
    assert result["calories"] == 640


def test_client_uses_api_key_basic_auth_and_browser_user_agent() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    client = IntervalsClient(settings(), httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.list_wellness(date(2026, 7, 1), date(2026, 7, 12)) == []
    assert client.list_activities(date(2026, 7, 1), date(2026, 7, 12)) == []
    assert str(requests[0].url).startswith(f"{BASE_URL}/athlete/0/wellness")
    assert "fields=hrvSDNN" in str(requests[0].url)
    assert str(requests[1].url).startswith(f"{BASE_URL}/athlete/0/activities")
    assert requests[0].headers["authorization"].startswith("Basic ")
    assert requests[0].headers["user-agent"].startswith("Mozilla/5.0")
