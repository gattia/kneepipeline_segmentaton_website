"""
Job model with Redis persistence.

The Job dataclass represents a processing job and handles its persistence to Redis.
Queue position is tracked using Redis sorted sets for efficient ordering.
"""
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

import redis


@dataclass
class Job:
    """
    Represents a processing job in the pipeline.

    Attributes:
        id: Unique job identifier (UUID)
        input_filename: Original filename uploaded by user
        input_path: Path to the validated input file
        options: Processing options dict
        status: Current job status (queued, processing, complete, error)
        created_at: ISO timestamp when job was created
        started_at: ISO timestamp when processing started
        completed_at: ISO timestamp when processing finished
        progress_percent: Current progress (0-100)
        current_step: Current processing step number
        total_steps: Total number of processing steps
        step_name: Human-readable name of current step
        result_path: Path to results zip file (when complete)
        result_size_bytes: Size of results file in bytes
        error_message: Error description (when failed)
        error_code: Error code for categorization
        retain_for_research: Whether user consented to research retention
        email: Optional user email for tracking/notifications
    """
    id: str
    input_filename: str
    input_path: str
    options: dict
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: int = 0
    current_step: int = 0
    total_steps: int = 4
    step_name: str = ""
    result_path: Optional[str] = None
    result_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retain_for_research: bool = True
    email: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert job to dictionary for serialization."""
        return asdict(self)

    def save(self, redis_client: redis.Redis) -> None:
        """
        Persist job state to Redis.

        Jobs are stored in a hash (jobs -> job_id -> job_json).
        Queued jobs are also tracked in a sorted set (job_queue) for position tracking.
        """
        # Save to hash
        redis_client.hset("jobs", self.id, json.dumps(self.to_dict()))

        # Track in queue if status is queued
        if self.status == "queued":
            # Use created_at timestamp as score for FIFO ordering
            score = datetime.fromisoformat(self.created_at).timestamp()
            redis_client.zadd("job_queue", {self.id: score})

    def delete_from_queue(self, redis_client: redis.Redis) -> None:
        """Remove job from queue tracking (called when processing starts)."""
        redis_client.zrem("job_queue", self.id)

    @classmethod
    def load(cls, job_id: str, redis_client: redis.Redis) -> Optional["Job"]:
        """
        Load job from Redis by ID.

        Returns None if job doesn't exist.
        """
        data = redis_client.hget("jobs", job_id)
        if data:
            return cls(**json.loads(data))
        return None

    @classmethod
    def get_queue_position(cls, job_id: str, redis_client: redis.Redis) -> int:
        """
        Get 1-indexed position in queue.

        Returns 0 if job is not in queue (already processing or complete).
        """
        rank = redis_client.zrank("job_queue", job_id)
        return rank + 1 if rank is not None else 0

    @classmethod
    def get_queue_length(cls, redis_client: redis.Redis) -> int:
        """Get total number of jobs currently in queue."""
        return redis_client.zcard("job_queue")
