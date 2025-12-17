# Stage 1: MVP Implementation

## Overview

Stage 1 builds a complete end-to-end prototype with **dummy processing**. Users can upload MRI files, see queue position, and download a dummy results zip file.

**Total Estimated Time**: ~4 hours

---

## Current Progress

| Stage | Status | Tests | Description |
|-------|--------|-------|-------------|
| **1.1** | ✅ Complete | 23 passing | Project scaffolding, FastAPI app, health endpoint |
| **1.2** | ✅ Complete | 36 passing | Pydantic schemas, Job model, services |
| **1.3** | ✅ Complete | 27 passing | Celery configuration, tasks, dummy worker |
| **1.4** | ✅ Complete | 22 passing | Upload, status, download, stats routes |
| **1.5** | ✅ Complete | - | Frontend UI with FilePond |
| **1.6** | ✅ Complete | 30 passing | Docker, docker-compose, deployment |
| **1.7** | ✅ Complete | 16 passing | HTTPS with Caddy reverse proxy |

**Total Tests**: 154 passing

### Quick Verification

```bash
make verify   # Run lint + all tests
make test     # Run all tests
```

---

## Sub-Stages

Execute these in order. Each is designed to be a focused task for an AI assistant.

| Stage | Name | Time | Verification | Completion Report |
|-------|------|------|--------------|-------------------|
| **1.1** | [Project Scaffolding](./STAGE_1.1_PROJECT_SCAFFOLDING.md) | ~30 min | `pytest -m stage_1_1` | [COMPLETED](./STAGE_1.1_COMPLETED.md) |
| **1.2** | [Models & Services](./STAGE_1.2_MODELS_AND_SERVICES.md) | ~45 min | `pytest -m stage_1_2` | [COMPLETED](./STAGE_1.2_COMPLETED.md) |
| **1.3** | [Redis + Celery](./STAGE_1.3_REDIS_AND_CELERY.md) | ~30 min | `pytest -m stage_1_3` | [COMPLETED](./STAGE_1.3_COMPLETED.md) |
| **1.4** | [API Routes](./STAGE_1.4_API_ROUTES.md) | ~45 min | `pytest -m stage_1_4` | [COMPLETED](./STAGE_1.4_COMPLETED.md) |
| **1.5** | [Frontend](./STAGE_1.5_FRONTEND.md) | ~45 min | `pytest -m stage_1_5` | [COMPLETED](./STAGE_1.5_COMPLETED.md) |
| **1.6** | [Docker & Deployment](./STAGE_1.6_DOCKER_AND_DEPLOYMENT.md) | ~60 min | `pytest -m stage_1_6` | [COMPLETED](./STAGE_1.6_COMPLETED.md) |
| **1.7** | [HTTPS with Caddy](./STAGE_1.7_HTTPS_CADDY.md) | ~30 min | `pytest -m stage_1_7` | [COMPLETED](./STAGE_1.7_HTTPS_CADDY.md) |

---

## Verification with pytest

Each sub-stage has pytest tests that verify completion. Tests are marked with stage identifiers.

### How to Verify a Stage

```bash
# Activate the conda environment first
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Verify a specific stage
pytest -m stage_1_1 -v

# Run all Stage 1 tests
pytest -m "stage_1_1 or stage_1_2 or stage_1_3 or stage_1_4 or stage_1_5 or stage_1_6 or stage_1_7" -v

# Run all tests
pytest -v
```

### Completion Criteria

- **All tests pass** = Stage is complete
- **Any test fails** = Stage is incomplete, fix the failing tests

### Test Files

Tests are organized in the `tests/` directory:

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (temp_dir, redis_client)
├── test_stage_1_1.py        # Project scaffolding
├── test_stage_1_2.py        # Models & services
├── test_stage_1_3.py        # Redis + Celery
├── test_stage_1_4.py        # API routes
├── test_stage_1_5.py        # Frontend
├── test_stage_1_6.py        # Docker & deployment
└── test_stage_1_7.py        # HTTPS with Caddy
```

> **Important**: All shared fixtures (`temp_dir`, `redis_client`) are in `conftest.py`. 
> Do **not** redefine these in individual test files.

### pytest Markers (in pyproject.toml)

```toml
[tool.pytest.ini_options]
markers = [
    "stage_1_1: Stage 1.1 - Project Scaffolding",
    "stage_1_2: Stage 1.2 - Models & Services",
    "stage_1_3: Stage 1.3 - Redis + Celery",
    "stage_1_4: Stage 1.4 - API Routes",
    "stage_1_5: Stage 1.5 - Frontend",
    "stage_1_6: Stage 1.6 - Docker & Deployment",
    "stage_1_7: Stage 1.7 - HTTPS with Caddy",
]
```

---

## Design Conventions

These conventions are followed across all stages to avoid redundancy and improve maintainability:

### 1. Centralized Configuration
- Environment variables are read **once** and exported (e.g., `REDIS_URL` in `celery_app.py`)
- Other modules **import** these values rather than re-reading from environment

### 2. Shared Test Fixtures
- Common fixtures (`temp_dir`, `redis_client`) are defined in `tests/conftest.py`
- Individual test files **do not redefine** these fixtures

### 3. Two Redis Client Patterns
| Function | Location | Use Case |
|----------|----------|----------|
| `get_redis_client()` | `job_service.py` | FastAPI routes (uses `Depends()`) |
| `get_redis_client()` | `tasks.py` | Celery tasks (standalone) |

### 4. Configurable Test Delays
- `dummy_pipeline()` has `simulate_delay` parameter
- **Default**: `True` (realistic delays for manual testing)
- **Tests**: Use `False` for fast execution

---

## Prerequisites

**Stage 0 must be complete.** See [STAGE_0_DEV_ENVIRONMENT.md](../STAGE_0_DEV_ENVIRONMENT.md).

You should have:
- ✅ GCP VM running (Debian 12)
- ✅ Miniconda installed with `kneepipeline` environment (Python 3.10)
- ✅ Docker running with Redis container on port 6379
- ✅ Build tools installed (gcc, curl, etc.)
- ✅ Git installed

---

## Development Strategy

We develop **directly on GCP** from the start:

1. **No GPU needed** - Stage 1 uses dummy processing (CPU only)
2. **Real environment** - Catch deployment issues early
3. **Cheap VM** - Start with `e2-medium` (~$25/month)
4. **Upgrade later** - Switch to GPU instance for Stage 3

---

## After Stage 1

Once complete, you'll have:

- ✅ Working web application accessible via HTTPS
- ✅ Full upload → queue → process → download flow
- ✅ User email tracking and statistics
- ✅ CI/CD pipeline running tests on push
- ✅ Docker-based deployment with Caddy reverse proxy
- ✅ Automatic SSL certificate management

**Next**: Stage 2 adds progress refinements and session persistence, Stage 3 integrates the real pipeline.
