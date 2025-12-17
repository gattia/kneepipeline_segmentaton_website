"""
Routes package - FastAPI route modules.

All routers are exported for registration in main.py.
"""
from . import download, health, stats, status, upload

__all__ = ["health", "upload", "status", "download", "stats"]
