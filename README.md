# Knee MRI Segmentation Website

A web application for automated knee MRI segmentation and analysis. Upload knee MRI data, get segmentations, 3D meshes, cartilage thickness measurements, and BScore computation.

## Quick Start

### Prerequisites

Complete the development environment setup first:
- See [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md)

### Development

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Start FastAPI server
uvicorn backend.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Architecture, API design, full specification |
| [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md) | GCP VM setup, Miniconda, Docker, Redis |
| [docs/STAGE_1_DETAILED_PLAN.md](docs/STAGE_1_DETAILED_PLAN.md) | MVP implementation details |
| [docs/stage_1/](docs/stage_1/) | Step-by-step guides for each component |

## Project Status

- [x] Stage 0: Development Environment
- [ ] Stage 1: MVP with Dummy Processing
- [ ] Stage 2: Progress & Statistics  
- [ ] Stage 3: Real Pipeline Integration

## License

Research use only. Not for clinical diagnosis.
