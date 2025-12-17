"""
Workers package - Celery app and task definitions.

Exports:
    celery_app: The configured Celery application
    REDIS_URL: Redis connection URL (for creating Redis clients in tasks)
    process_pipeline: Main processing Celery task
    dummy_pipeline: Phase 1 dummy processing function
"""
from .celery_app import REDIS_URL, celery_app
from .dummy_worker import dummy_pipeline
from .tasks import process_pipeline

__all__ = [
    "celery_app",
    "REDIS_URL",
    "process_pipeline",
    "dummy_pipeline",
]
