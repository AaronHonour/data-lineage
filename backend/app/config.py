"""Application configuration management."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Data Lineage Tool"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        env="ALLOWED_ORIGINS"
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://lineage:lineage@localhost:5432/lineage",
        env="DATABASE_URL"
    )
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=0, env="DB_MAX_OVERFLOW")
    db_echo: bool = Field(default=False, env="DB_ECHO")

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    encryption_key: str = Field(
        default="your-encryption-key-change-in-production",
        env="ENCRYPTION_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=60 * 24,  # 24 hours
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Background Jobs
    enable_scheduler: bool = Field(default=True, env="ENABLE_SCHEDULER")
    default_sync_interval: int = Field(
        default=3600,  # 1 hour
        env="DEFAULT_SYNC_INTERVAL"
    )

    # Lineage Processing
    max_lineage_depth: int = Field(default=10, env="MAX_LINEAGE_DEPTH")
    max_graph_nodes: int = Field(default=1000, env="MAX_GRAPH_NODES")

    @property
    def async_database_url(self) -> str:
        """Get async database URL as string."""
        return str(self.database_url)


# Global settings instance
settings = Settings()
