# Stage 1: MVP Implementation

## Overview

Stage 1 builds a complete end-to-end prototype with **dummy processing**. Users can upload MRI files, see queue position, and download a dummy results zip file.

**Total Estimated Time**: ~4 hours

---

## Current Progress

| Stage | Status | Tests | Description |
|-------|--------|-------|-------------|
| **1.1** | ✅ Complete | 23 passing | Project scaffolding, FastAPI app, health endpoint |
| **1.2** | ✅ Complete | 35 passing | Pydantic schemas, Job model, services |
| **1.3** | ⬜ Not Started | - | Celery configuration, tasks, dummy worker |
| **1.4** | ⬜ Not Started | - | Upload, status, download, stats routes |
| **1.5** | ⬜ Not Started | - | Frontend UI with FilePond |
| **1.6** | ⬜ Not Started | - | Docker, docker-compose, deployment |

**Total Tests**: 58 passing (as of Stage 1.2)

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
| **1.3** | [Redis + Celery](./STAGE_1.3_REDIS_AND_CELERY.md) | ~30 min | `pytest -m stage_1_3` | - |
| **1.4** | [API Routes](./STAGE_1.4_API_ROUTES.md) | ~45 min | `pytest -m stage_1_4` | - |
| **1.5** | [Frontend](./STAGE_1.5_FRONTEND.md) | ~45 min | `pytest -m stage_1_5` | - |
| **1.6** | [Docker & Deployment](./STAGE_1.6_DOCKER_AND_DEPLOYMENT.md) | ~45 min | `pytest -m stage_1_6` | - |

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
pytest -m "stage_1_1 or stage_1_2 or stage_1_3 or stage_1_4 or stage_1_5 or stage_1_6" -v

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
├── conftest.py              # Shared fixtures
├── test_stage_1_1.py        # Project scaffolding
├── test_stage_1_2.py        # Models & services
├── test_stage_1_3.py        # Redis + Celery
├── test_stage_1_4.py        # API routes
├── test_stage_1_5.py        # Frontend
└── test_stage_1_6.py        # Docker & deployment
```

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
]
```

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

- ✅ Working web application accessible via public IP
- ✅ Full upload → queue → process → download flow
- ✅ User email tracking and statistics
- ✅ CI/CD pipeline running tests on push
- ✅ Docker-based deployment

**Next**: Stage 2 adds progress refinements and session persistence, Stage 3 integrates the real pipeline.
