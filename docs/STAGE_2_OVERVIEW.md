# Stage 2: Progress & Statistics

## Overview

**Goal**: Polish the user experience with better progress feedback, time estimates, and session persistence.

**Estimated Time**: 3-5 days

**Prerequisites**: Stage 1 complete (working upload → process → download flow)

---

## What This Stage Adds

| Feature | Description |
|---------|-------------|
| **Progress Polling** | Frontend polls `/status/{job_id}` every 2 seconds for real-time updates |
| **Time Estimation** | Track processing times, show ETA based on rolling average |
| **Session Persistence** | Store job_id in localStorage so users can resume after browser close |
| **Enhanced Statistics** | Persist stats in Redis, show processing history |

---

## Task Breakdown

### 2.1: Progress Polling (~1 day)

**Current State**: Frontend polls but shows basic status  
**Goal**: Smooth progress bar with step names

- [ ] Update `/status` response to include `progress_percent`, `current_step`
- [ ] Frontend: Update progress bar in real-time (every 2 seconds)
- [ ] Frontend: Display current processing step (e.g., "Segmenting...", "Generating meshes...")
- [ ] Frontend: Show queue position when status is `queued`

### 2.2: Time Estimation (~1 day)

**Goal**: Show "Estimated time remaining" based on historical data

- [ ] Track processing duration for each completed job in Redis
- [ ] Calculate rolling average (last 20 jobs)
- [ ] Include `eta_seconds` in `/status` response
- [ ] Frontend: Display ETA countdown

**Implementation Notes**:
- Store `processing_times` as Redis list (LPUSH/LTRIM for rolling window)
- ETA = average_time × (1 - progress_percent)

### 2.3: Session Persistence (~1 day)

**Goal**: Users can close browser and return to see their job status

- [ ] On job creation: Store `job_id` in `localStorage`
- [ ] On page load: Check for existing `job_id`, prompt "Resume previous job?"
- [ ] Clear `localStorage` when:
  - Download completes
  - Job expires (24 hours)
  - User starts new upload
- [ ] Handle edge cases:
  - Job not found (expired)
  - Different browser/device (graceful degradation)

### 2.4: Enhanced Statistics (~0.5 day)

**Goal**: More detailed usage stats

- [ ] Track jobs by status (completed, failed, expired)
- [ ] Track average processing time
- [ ] Persist stats across Redis restarts (RDB snapshots already enabled)
- [ ] Optional: Track anonymous usage patterns (files per day histogram)

---

## API Changes

### Updated `/status/{job_id}` Response

```json
{
  "job_id": "abc123",
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Generating meshes",
  "queue_position": null,
  "eta_seconds": 180,
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:05Z"
}
```

### Updated `/stats` Response

```json
{
  "total_jobs": 150,
  "completed_jobs": 142,
  "failed_jobs": 3,
  "active_jobs": 5,
  "average_processing_time_seconds": 420
}
```

---

## Frontend Changes

### Progress Display

```
┌─────────────────────────────────────────────────┐
│  Processing your MRI...                         │
│                                                 │
│  [████████████░░░░░░░░░░░░░░] 45%              │
│                                                 │
│  Current step: Generating meshes                │
│  Estimated time remaining: ~3 minutes           │
└─────────────────────────────────────────────────┘
```

### Session Resume Prompt

```
┌─────────────────────────────────────────────────┐
│  📋 Resume Previous Job?                        │
│                                                 │
│  You have a job from 2 hours ago that may       │
│  still be processing.                           │
│                                                 │
│  [Check Status]    [Start New Upload]           │
└─────────────────────────────────────────────────┘
```

---

## Testing Strategy

| Test | Description |
|------|-------------|
| `test_status_includes_progress` | Verify progress fields in response |
| `test_eta_calculation` | Verify ETA based on mock timing data |
| `test_stats_persistence` | Stats survive Redis restart |
| `test_localstorage_integration` | E2E test with browser (Playwright/Selenium) |

---

## Files to Modify/Create

| File | Changes |
|------|---------|
| `backend/routes/status.py` | Add progress_percent, eta_seconds |
| `backend/services/statistics.py` | Track processing times, calculate averages |
| `frontend/js/app.js` | localStorage handling, progress UI |
| `frontend/css/styles.css` | Progress bar styling |
| `tests/test_stage_2.py` | New test file |

---

## Success Criteria

- [ ] Progress bar updates smoothly during processing
- [ ] ETA shown and reasonably accurate (±20%)
- [ ] User can close browser, return, and see job status
- [ ] Stats page shows completed/failed counts
- [ ] All new tests pass

---

## Notes

- **No WebSocket needed**: HTTP polling every 2 seconds is sufficient and works through all proxies
- **localStorage limitations**: Only works in same browser; consider future email notification feature for cross-device support
- **Privacy**: No PII stored; job_ids are random UUIDs

---

## References

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - Full architecture details
- [Stage 1 README](./stage_1/README.md) - Completed MVP components
