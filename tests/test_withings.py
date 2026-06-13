from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from health_observatory.config import Settings
from health_observatory.sync.withings import (
    MEASURE_URL,
    TOKEN_URL,
    WithingsApiError,
    WithingsClient,
    normalize_measure_group,
)


def settings() -> Settings:
    return Settings(
        withings_client_id="client-id",
        withings_client_secret=SecretStr("client-secret"),
        withings_refresh_token=SecretStr("refresh-token"),
    )


def test_normalize_measure_group_preserves_unknown_measurements() -> None:
    group = {
        "grpid": 42,
        "date": 1_700_000_000,
        "measures": [
            {"type": 1, "value": 72345, "unit": -3},
            {"type": 6, "value": 214, "unit": -1},
            {"type": 999, "value": 12, "unit": -1},
        ],
    }

    result = normalize_measure_group(group)

    assert result["timestamp"] == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert result["withings_grpid"] == 42
    assert result["weight_kg"] == pytest.approx(72.345)
    assert result["fat_ratio_pct"] == pytest.approx(21.4)
    assert result["unknown_measurements"] == [
        {"type": 999, "value": 12, "unit": -1, "scaled_value": pytest.approx(1.2)}
    ]
    assert result["raw_payload"] == group


def test_client_refreshes_token_and_paginates_measurements() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if str(request.url) == TOKEN_URL:
            return httpx.Response(
                200,
                json={
                    "status": 0,
                    "body": {"access_token": "access", "refresh_token": "rotated"},
                },
            )
        offset = request.content.decode()
        if "offset=0" in offset:
            return httpx.Response(
                200,
                json={
                    "status": 0,
                    "body": {"measuregrps": [{"grpid": 1}], "more": 1, "offset": 10},
                },
            )
        return httpx.Response(
            200,
            json={"status": 0, "body": {"measuregrps": [{"grpid": 2}], "more": 0}},
        )

    client = WithingsClient(settings(), httpx.Client(transport=httpx.MockTransport(handler)))

    tokens = client.refresh_access_token("refresh-token")
    groups = client.get_measure_groups(
        tokens.access_token, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
    )

    assert tokens.refresh_token == "rotated"
    assert groups == [{"grpid": 1}, {"grpid": 2}]
    assert len(requests) == 3
    assert str(requests[1].url) == MEASURE_URL
    assert requests[1].headers["authorization"] == "Bearer access"


def test_client_raises_for_withings_status() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": 401, "body": {}})

    client = WithingsClient(settings(), httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(WithingsApiError, match="status 401"):
        client.refresh_access_token("bad-token")
