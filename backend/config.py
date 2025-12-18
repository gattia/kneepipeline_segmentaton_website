from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    debug: bool = False
    max_upload_size_mb: int = 600

    # Directories - defaults to mounted disk location for production
    # These can be overridden via environment variables or .env file
    # In Docker: /app/data/* (bind mounted to /mnt/data/knee_pipeline_data)
    # Native: /mnt/data/knee_pipeline_data/* or ./data/* for development
    upload_dir: Path = Path("/mnt/data/knee_pipeline_data/uploads")
    temp_dir: Path = Path("/mnt/data/knee_pipeline_data/temp")
    log_dir: Path = Path("/mnt/data/knee_pipeline_data/logs")
    results_dir: Path = Path("/mnt/data/knee_pipeline_data/results")

    # Results
    results_expiry_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
