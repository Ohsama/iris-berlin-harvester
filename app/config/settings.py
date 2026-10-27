from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    No credentials are ever committed to source code.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="iris_intelligence", alias="POSTGRES_DB")
    database_schema: str = Field(default="iris_staging", alias="DATABASE_SCHEMA")

    # Scraper
    harvester_source_url: str = Field(default="https://berlin.de/bebauungsplaene", alias="HARVESTER_SOURCE_URL")
    use_offline_fixtures: bool = Field(default=True, alias="USE_OFFLINE_FIXTURES")
    fixtures_dir: str = Field(default="fixtures", alias="FIXTURES_DIR")
    request_timeout_seconds: int = Field(default=30, alias="REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
