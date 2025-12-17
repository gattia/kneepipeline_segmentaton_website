"""
Celery application configuration.

This module configures Celery with Redis as both the message broker
and result backend. It's designed for single-worker GPU processing.

Exports:
    celery_app: The configured Celery application instance
    REDIS_URL: Redis connection URL (used by tasks.py for Redis client)
"""
import os

from celery import Celery

# Redis URL from environment or default
# NOTE: This is exported and imported by tasks.py to avoid duplication
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "knee_pipeline", broker=REDIS_URL, backend=REDIS_URL, include=["backend.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking - allows us to see when task starts
    task_track_started=True,
    # Single worker for GPU constraint (one job at a time)
    worker_concurrency=1,
    # Acknowledge after completion (handles crashes gracefully)
    # If worker crashes mid-task, task will be requeued
    task_acks_late=True,
    # Prefetch only 1 task at a time (important for GPU memory)
    worker_prefetch_multiplier=1,
    # Retry configuration
    task_default_retry_delay=60,  # Wait 60s before retry
    task_max_retries=2,  # Max 2 retries
    # Result expiration (24 hours)
    result_expires=86400,
    # Don't store successful task results (we use Redis directly for job status)
    task_ignore_result=False,
)
