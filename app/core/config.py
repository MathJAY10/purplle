from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Store Intelligence System", validation_alias="APP_NAME")
    app_env: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="store_intelligence", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="store_user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="store_password", validation_alias="POSTGRES_PASSWORD")
    postgres_pool_size: int = Field(default=5, validation_alias="POSTGRES_POOL_SIZE")
    postgres_max_overflow: int = Field(default=10, validation_alias="POSTGRES_MAX_OVERFLOW")

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")
    redis_password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")
    redis_stream_name: str = Field(default="store_intelligence.events", validation_alias="REDIS_STREAM_NAME")
    redis_consumer_group: str = Field(default="store-intelligence-workers", validation_alias="REDIS_CONSUMER_GROUP")
    redis_consumer_name: str = Field(default="worker-1", validation_alias="REDIS_CONSUMER_NAME")

    cv_confidence_threshold: float = Field(default=0.35, validation_alias="CV_CONFIDENCE_THRESHOLD")
    cv_frame_skip: int = Field(default=2, validation_alias="CV_FRAME_SKIP")
    cv_debounce_frames: int = Field(default=15, validation_alias="CV_DEBOUNCE_FRAMES")
    cv_track_ttl_frames: int = Field(default=45, validation_alias="CV_TRACK_TTL_FRAMES")
    cv_debug_visualization: bool = Field(default=False, validation_alias="CV_DEBUG_VISUALIZATION")
    cv_line_x1: int = Field(default=100, validation_alias="CV_LINE_X1")
    cv_line_y1: int = Field(default=100, validation_alias="CV_LINE_Y1")
    cv_line_x2: int = Field(default=500, validation_alias="CV_LINE_X2")
    cv_line_y2: int = Field(default=100, validation_alias="CV_LINE_Y2")
    health_stale_feed_seconds: int = Field(default=300, validation_alias="HEALTH_STALE_FEED_SECONDS")
    store_config_dir: str = Field(default="configs/stores", validation_alias="STORE_CONFIG_DIR")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
