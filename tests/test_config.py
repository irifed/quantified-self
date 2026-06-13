import pytest
from pydantic import SecretStr

from health_observatory.config import Settings


def test_require_withings_credentials_reports_missing_values() -> None:
    settings = Settings(
        withings_client_id="client",
        withings_client_secret=SecretStr(""),
        withings_refresh_token=SecretStr(""),
    )

    with pytest.raises(ValueError, match="WITHINGS_CLIENT_SECRET, WITHINGS_REFRESH_TOKEN"):
        settings.require_withings_credentials()
