from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from health_observatory.config import Settings
from health_observatory.models import BodyComposition, SyncState

TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
MEASURE_URL = "https://wbsapi.withings.net/measure"

MEASURE_FIELDS = {
    1: "weight_kg",
    5: "fat_free_mass_kg",
    6: "fat_ratio_pct",
    8: "fat_mass_kg",
    76: "muscle_mass_kg",
    77: "hydration_kg",
    88: "bone_mass_kg",
}


class WithingsApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class WithingsTokens:
    access_token: str
    refresh_token: str


def scaled_value(measure: dict[str, Any]) -> float:
    return float(measure["value"]) * (10.0 ** int(measure["unit"]))


def normalize_measure_group(group: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "timestamp": datetime.fromtimestamp(int(group["date"]), tz=UTC),
        "withings_grpid": int(group["grpid"]),
        "source": "withings",
        "raw_payload": group,
        "unknown_measurements": [],
    }
    for measure in group.get("measures", []):
        measure_type = int(measure["type"])
        value = scaled_value(measure)
        field = MEASURE_FIELDS.get(measure_type)
        if field is None:
            normalized["unknown_measurements"].append({**measure, "scaled_value": value})
        else:
            normalized[field] = value
    return normalized


class WithingsClient:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=30.0)

    def __enter__(self) -> "WithingsClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.http.close()

    def refresh_access_token(self, refresh_token: str) -> WithingsTokens:
        response = self.http.post(
            TOKEN_URL,
            data={
                "action": "requesttoken",
                "grant_type": "refresh_token",
                "client_id": self.settings.withings_client_id,
                "client_secret": self.settings.withings_client_secret.get_secret_value(),
                "refresh_token": refresh_token,
            },
        )
        body = self._checked_body(response)
        return WithingsTokens(
            access_token=str(body["access_token"]), refresh_token=str(body["refresh_token"])
        )

    def get_measure_groups(
        self, access_token: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.http.post(
                MEASURE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                data={
                    "action": "getmeas",
                    "category": 1,
                    "startdate": int(start.timestamp()),
                    "enddate": int(end.timestamp()),
                    "offset": offset,
                },
            )
            body = self._checked_body(response)
            groups.extend(body.get("measuregrps", []))
            if not body.get("more"):
                return groups
            offset = int(body["offset"])

    @staticmethod
    def _checked_body(response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        payload = response.json()
        if int(payload.get("status", -1)) != 0:
            raise WithingsApiError(f"Withings API returned status {payload.get('status')}")
        body = payload.get("body")
        if not isinstance(body, dict):
            raise WithingsApiError("Withings API response did not contain a body")
        return body


def sync_withings(session: Session, settings: Settings, client: WithingsClient) -> int:
    settings.require_withings_credentials()
    state = session.get(SyncState, "withings")
    configured_refresh_token = settings.withings_refresh_token.get_secret_value()
    cursor = state.cursor if state and state.cursor else {}
    refresh_token = str(cursor.get("refresh_token") or configured_refresh_token)
    tokens = client.refresh_access_token(refresh_token)

    if state is None:
        state = SyncState(source="withings")
        session.add(state)
    state.cursor = {"refresh_token": tokens.refresh_token}
    session.commit()

    now = datetime.now(UTC)
    if state and state.last_sync:
        start = state.last_sync - timedelta(days=1)
    else:
        start = now - timedelta(days=settings.initial_sync_days)

    groups = client.get_measure_groups(tokens.access_token, start, now)
    rows = [normalize_measure_group(group) for group in groups]
    if rows:
        statement = insert(BodyComposition).values(rows)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[BodyComposition.timestamp, BodyComposition.withings_grpid],
            set_={
                "weight_kg": excluded.weight_kg,
                "fat_ratio_pct": excluded.fat_ratio_pct,
                "fat_mass_kg": excluded.fat_mass_kg,
                "fat_free_mass_kg": excluded.fat_free_mass_kg,
                "muscle_mass_kg": excluded.muscle_mass_kg,
                "hydration_kg": excluded.hydration_kg,
                "bone_mass_kg": excluded.bone_mass_kg,
                "raw_payload": excluded.raw_payload,
                "unknown_measurements": excluded.unknown_measurements,
            },
        )
        session.execute(statement)

    state.last_sync = now
    return len(rows)
