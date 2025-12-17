# Knee MRI Segmentation Website

A web application for automated knee MRI segmentation and analysis. Upload knee MRI data, get segmentations, 3D meshes, cartilage thickness measurements, and BScore computation.

## Quick Start

### Prerequisites

1. Complete the development environment setup:
   - See [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md)

2. Ensure Redis is running:
   ```bash
   make redis-start
   # or: docker start redis
   ```

### Installation

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
make install
# or: pip install -r backend/requirements.txt
```

### Development

```bash
# Start FastAPI server
make run
# or: uvicorn backend.main:app --reload --port 8000

# Start Celery worker (separate terminal)
make worker
# or: celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1
```

Then open http://localhost:8000 in your browser.

### Docker Deployment (Production)

```bash
cd ~/programming/kneepipeline_segmentaton_website

# Stop any existing Redis running outside Docker
docker stop redis 2>/dev/null || true

# Create environment file
cp docker/.env.example docker/.env

# Build and start all services
cd docker
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

**Services started:**
- `knee-pipeline-caddy` - Reverse proxy with auto-HTTPS (ports 80, 443)
- `knee-pipeline-redis` - Redis (internal only)
- `knee-pipeline-web` - FastAPI (internal only)
- `knee-pipeline-worker` - Celery worker

**Access via HTTPS:** `https://openmsk.com`

> **Note**: The application uses Caddy for automatic HTTPS. Access via domain name, not IP address.
> See [docs/stage_1/STAGE_1.7_HTTPS_CADDY.md](docs/stage_1/STAGE_1.7_HTTPS_CADDY.md) for setup details.

---

## Testing

We use **pytest** for testing. Tests are organized by development stage.

```bash
# Run all tests
make test

# Run specific stage tests
make test-stage-1-1
make test-stage-1-2

# Run with coverage report
make test-cov
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `stage_1_1` | Project scaffolding, health endpoint |
| `stage_1_2` | Models and services |
| `stage_1_3` | Redis + Celery workers |
| `stage_1_4` | API routes |
| `stage_1_5` | Frontend |
| `stage_1_6` | Docker & deployment |
| `stage_1_7` | HTTPS with Caddy |

Run a specific marker:
```bash
pytest -m stage_1_2 -v
```

---

## Linting

We use **ruff** for linting and formatting (configured in `pyproject.toml`).

```bash
# Check for issues
make lint

# Auto-fix issues
make format
```

Or run directly:
```bash
ruff check backend/ tests/           # Check
ruff check backend/ tests/ --fix     # Fix
ruff format backend/ tests/          # Format
```

---

## Makefile Commands

Run `make help` to see all available commands:

| Command | Description |
|---------|-------------|
| `make install` | Install Python dependencies |
| `make test` | Run all tests |
| `make test-cov` | Run tests with coverage |
| `make lint` | Check code with ruff |
| `make format` | Auto-fix linting issues |
| `make run` | Start FastAPI server |
| `make worker` | Start Celery worker |
| `make redis-start` | Start Redis container |
| `make verify` | Run lint + tests (CI check) |
| `make clean` | Remove cache files |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Architecture, API design, full specification |
| [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md) | GCP VM setup, Miniconda, Docker, Redis |
| [docs/STAGE_1_DETAILED_PLAN.md](docs/STAGE_1_DETAILED_PLAN.md) | MVP implementation details |
| [docs/stage_1/](docs/stage_1/) | Step-by-step guides for Stage 1 components |
| [docs/STAGE_2_OVERVIEW.md](docs/STAGE_2_OVERVIEW.md) | Progress & statistics enhancements |
| [docs/STAGE_3_OVERVIEW.md](docs/STAGE_3_OVERVIEW.md) | Real pipeline integration with GPU |

---

## Project Status

- [x] Stage 0: Development Environment
- [x] Stage 1.1: Project Scaffolding
- [x] Stage 1.2: Models & Services
- [x] Stage 1.3: Redis & Celery
- [x] Stage 1.4: API Routes
- [x] Stage 1.5: Frontend
- [x] Stage 1.6: Docker & Deployment
- [x] Stage 1.7: HTTPS with Caddy
- [ ] Stage 2: Progress & Statistics  
- [ ] Stage 3: Real Pipeline Integration

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (Redis, worker status) |
| `/upload` | POST | Upload file and start processing |
| `/status/{job_id}` | GET | Get job status |
| `/download/{job_id}` | GET | Download results |
| `/stats` | GET | Usage statistics |
| `/docs` | GET | OpenAPI documentation |

---

## License

Research use only. Not for clinical diagnosis.
