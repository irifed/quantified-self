from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://health:change_me@timescaledb:5432/health"
    withings_client_id: str = ""
    withings_client_secret: SecretStr = SecretStr("")
    withings_refresh_token: SecretStr = SecretStr("")
    timezone: str = Field(default="Europe/Amsterdam", validation_alias="TZ")
    sync_interval_hours: int = Field(default=6, ge=1, le=168)
    log_level: str = "INFO"
    initial_sync_days: int = Field(default=3650, ge=1)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def require_withings_credentials(self) -> None:
        missing = [
            name
            for name, value in (
                ("WITHINGS_CLIENT_ID", self.withings_client_id),
                ("WITHINGS_CLIENT_SECRET", self.withings_client_secret.get_secret_value()),
                ("WITHINGS_REFRESH_TOKEN", self.withings_refresh_token.get_secret_value()),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required Withings settings: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
