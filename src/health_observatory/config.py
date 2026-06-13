from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    postgres_db: str = "health"
    postgres_user: str = "health"
    postgres_password: SecretStr = SecretStr("change_me")
    database_host: str = "timescaledb"
    database_port: int = 5432
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

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

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
