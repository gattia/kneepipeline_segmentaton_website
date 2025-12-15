# Stage 1.2: Models & Services

## Overview

**Goal**: Create the data models and service layer that the API routes will use.

**Estimated Time**: ~30 minutes

**Deliverable**: All Pydantic schemas, Job model, and service modules ready for use.

---

## What This Stage Covers

1. **Pydantic Schemas** - `backend/models/schemas.py`
   - Request/response models for all endpoints
   - UploadOptions, StatusQueued, StatusProcessing, StatusComplete, StatusError, StatsResponse

2. **Job Model** - `backend/models/job.py`
   - Job dataclass with Redis persistence methods
   - Queue position tracking

3. **File Handler Service** - `backend/services/file_handler.py`
   - Validate uploaded files
   - Extract zip files
   - Find medical images in extracted contents

4. **Job Service** - `backend/services/job_service.py`
   - Redis client helper
   - Queue position and wait time calculations

5. **Statistics Service** - `backend/services/statistics.py`
   - Track total jobs, daily counts, unique users
   - Email tracking functions

---

## Success Criteria

- [ ] All model files created with no import errors
- [ ] Can import models in Python REPL without errors
- [ ] Unit tests pass for file validation logic

---

## Detailed Steps

*(To be expanded)*
