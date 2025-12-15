# Stage 1: MVP Implementation

## Overview

Stage 1 builds a complete end-to-end prototype with **dummy processing**. Users can upload MRI files, see queue position, and download a dummy results zip file.

**Total Estimated Time**: ~4 hours

---

## Sub-Stages

Execute these in order. Each is designed to be a focused task for an AI assistant.

| Stage | Name | Time | Description |
|-------|------|------|-------------|
| **1.1** | [Project Scaffolding](./STAGE_1.1_PROJECT_SCAFFOLDING.md) | ~30 min | GCP VM, directory structure, FastAPI basics |
| **1.2** | [Models & Services](./STAGE_1.2_MODELS_AND_SERVICES.md) | ~30 min | Pydantic schemas, Job model, service layer |
| **1.3** | [Redis + Celery](./STAGE_1.3_REDIS_AND_CELERY.md) | ~30 min | Job queue, dummy worker, task execution |
| **1.4** | [API Routes](./STAGE_1.4_API_ROUTES.md) | ~45 min | All REST endpoints wired up |
| **1.5** | [Frontend](./STAGE_1.5_FRONTEND.md) | ~45 min | Complete web UI |
| **1.6** | [Docker & Deployment](./STAGE_1.6_DOCKER_AND_DEPLOYMENT.md) | ~45 min | Containerization, GCP deployment, CI/CD |

---

## Prerequisites

Before starting Stage 1.1:

- GCP account with a project created
- Ability to create VM instances (no GPU quota needed yet)
- SSH key configured for GCP access
- Git installed locally

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
