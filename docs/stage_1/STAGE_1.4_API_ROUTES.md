# Stage 1.4: API Routes

## Overview

**Goal**: Implement all API endpoints and wire them to the services and Celery tasks.

**Estimated Time**: ~45 minutes

**Deliverable**: Fully functional REST API that can be tested with curl.

---

## What This Stage Covers

1. **Upload Route** - `backend/routes/upload.py`
   - Accept multipart form data (file + options + email)
   - Validate file, save to disk, create job
   - Submit Celery task
   - Return job_id and queue position

2. **Status Route** - `backend/routes/status.py`
   - Return current job status (queued/processing/complete/error)
   - Include progress percentage, step name, ETA

3. **Download Route** - `backend/routes/download.py`
   - Serve results zip file
   - Validate job is complete before serving

4. **Stats Route** - `backend/routes/stats.py`
   - Return usage statistics (total jobs, unique users, avg time)

5. **Router Registration** - Update `main.py` to include all routers

6. **Manual Testing** - Test each endpoint with curl/httpie

---

## Success Criteria

- [ ] POST /upload accepts a file and returns job_id
- [ ] GET /status/{job_id} returns correct status as job progresses
- [ ] GET /download/{job_id} returns the results zip
- [ ] GET /stats returns usage statistics
- [ ] All endpoints return proper error responses for invalid inputs

---

## Detailed Steps

*(To be expanded)*
