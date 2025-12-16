from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routes import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: create directories
    settings = get_settings()
    for dir_path in [settings.upload_dir, settings.temp_dir,
                     settings.log_dir, settings.results_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Knee MRI Analysis Pipeline",
    description="Automated knee MRI segmentation and analysis",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for development
settings = get_settings()
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

# Routes
app.include_router(health.router, tags=["Health"])

# Serve frontend static files (only if frontend directory exists)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
