# Stage 1.3: Redis + Celery Setup

## Overview

**Goal**: Set up Redis and Celery for job queue management, with a working dummy worker.

**Estimated Time**: ~30 minutes

**Deliverable**: A Celery task that can be triggered and completes successfully.

---

## What This Stage Covers

1. **Redis Installation** - Install and run Redis on the GCP VM (via Docker)

2. **Celery Configuration** - `backend/workers/celery_app.py`
   - Broker and backend configuration
   - Worker settings (concurrency=1, task tracking)

3. **Dummy Worker** - `backend/workers/dummy_worker.py`
   - SimpleITK-based image validation
   - Create zeroed image copy
   - Generate dummy results JSON/CSV
   - Package into zip file

4. **Celery Tasks** - `backend/workers/tasks.py`
   - Main `process_pipeline` task
   - Progress updates to Redis
   - Statistics recording on completion

5. **Testing** - Verify end-to-end task execution
   - Submit a task manually
   - Verify it completes and creates output

---

## Success Criteria

- [ ] Redis running and accessible (`redis-cli ping` returns PONG)
- [ ] Celery worker starts without errors
- [ ] Can submit a task via Python shell and see it complete
- [ ] Dummy results zip file is created

---

## Detailed Steps

*(To be expanded)*
