"""
Shared pytest fixtures for all test modules.
"""
import tempfile
from pathlib import Path

import pytest
import redis


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def redis_client():
    """
    Get a Redis client for testing.

    Uses database 15 (separate from production db 0) and flushes before/after tests.
    Requires Redis to be running on localhost:6379.
    """
    client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
    client.flushdb()  # Clean before test
    yield client
    client.flushdb()  # Clean after test
    client.close()
