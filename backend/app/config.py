"""Application settings, loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

from datetime import time
from functools import lru_cache
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEV_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ----- General -----
    app_name: str = "CAC Share Sessions"
    environment: Literal["development", "production", "test"] = "development"
    secret_key: str = _DEV_SECRET
    database_url: str = "sqlite:///./data/app.db"
    public_base_url: str = "http://localhost:5173"
    timezone: str = "Asia/Shanghai"
    frontend_dist: str = "../frontend/dist"
    log_level: str = "INFO"

    # ----- Accounts -----
    allow_registration: bool = True
    allowed_email_domains: Annotated[list[str], NoDecode] = Field(default_factory=list)
    bootstrap_admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)
    session_ttl_hours: int = 24 * 14
    password_reset_ttl_minutes: int = 120
    cookie_secure: bool | None = None  # defaults to True in production

    # ----- Scheduling rules -----
    day_start: time = time(9, 0)
    day_end: time = time(22, 0)
    slot_minutes: int = 30
    reviewer_limit: int = 3
    meetup_weekday: int = 6  # 0 = Monday ... 6 = Sunday
    meetup_window_start: time = time(14, 0)
    meetup_window_end: time = time(18, 0)
    close_grace_minutes: int = 24 * 60
    observer_rating_weight: int = 10

    # ----- Participation watch -----
    participation_lookback_days: int = 14
    participation_report_weekday: int = 6
    participation_report_hour: int = 22
    participation_report_email: str = ""
    review_reminder_interval_hours: int = 24

    # ----- Email -----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    mail_from: str = ""
    mail_from_name: str = "CAC Share Sessions"

    # ----- Background jobs -----
    run_scheduler: bool = False  # run jobs inside the web process (handy for single-process dev setups)
    scheduler_interval_seconds: int = 60

    @field_validator("allowed_email_domains", "bootstrap_admin_emails", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _check(self) -> Settings:
        if self.environment == "production" and self.secret_key == _DEV_SECRET:
            raise ValueError("SECRET_KEY must be set to a long random value in production")
        if self.day_start >= self.day_end:
            raise ValueError("DAY_START must be earlier than DAY_END")
        if self.meetup_window_start >= self.meetup_window_end:
            raise ValueError("MEETUP_WINDOW_START must be earlier than MEETUP_WINDOW_END")
        if 60 % self.slot_minutes != 0:
            raise ValueError("SLOT_MINUTES must divide 60 evenly")
        ZoneInfo(self.timezone)  # raises if the zone is unknown
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def secure_cookies(self) -> bool:
        return self.is_production if self.cookie_secure is None else self.cookie_secure

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host and self.mail_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()
