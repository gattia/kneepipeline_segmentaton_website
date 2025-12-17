from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    debug: bool = True
    max_upload_size_mb: int = 600

    # Directories
    upload_dir: Path = Path("./data/uploads")
    temp_dir: Path = Path("./data/temp")
    log_dir: Path = Path("./data/logs")
    results_dir: Path = Path("./data/results")

    # Results
    results_expiry_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
