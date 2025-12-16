"""
Pytest configuration and shared fixtures.
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from backend.main import app
    return TestClient(app)
