# Stage 3: Real Pipeline Integration

## Overview

Stage 3 integrates the actual knee MRI segmentation pipeline into the web application, replacing the dummy worker with real processing capabilities.

## Steps

| Step | Document | Description | Time |
|------|----------|-------------|------|
| 3.1 | [STAGE_3.1_PIPELINE_DEPENDENCIES.md](./STAGE_3.1_PIPELINE_DEPENDENCIES.md) | Install PyTorch, NSM, DOSMA, nnU-Net | 1-2 hrs |
| 3.2 | [STAGE_3.2_MODEL_DOWNLOAD.md](./STAGE_3.2_MODEL_DOWNLOAD.md) | Download models, create config.json | 30-60 min |
| 3.3 | [STAGE_3.3_PIPELINE_WORKER.md](./STAGE_3.3_PIPELINE_WORKER.md) | Create real pipeline worker | 2-3 hrs |
| 3.4 | [STAGE_3.4_CONFIG_MAPPING.md](./STAGE_3.4_CONFIG_MAPPING.md) | Map web options to pipeline config | 1 hr |
| 3.5 | [STAGE_3.5_ERROR_HANDLING.md](./STAGE_3.5_ERROR_HANDLING.md) | Add error handling & progress | 1-2 hrs |
| 3.6 | [STAGE_3.6_INTEGRATION_TESTING.md](./STAGE_3.6_INTEGRATION_TESTING.md) | End-to-end testing | 1-2 hrs |

**Total Estimated Time**: ~1 week

## Prerequisites

- Stage 1 complete (web application working with dummy processor)
- GPU-enabled GCP VM with T4 or better
- NVIDIA drivers and CUDA installed
- Docker with NVIDIA Container Toolkit

## Quick Reference

### Check GPU Status
```bash
nvidia-smi
```

### Start Services
```bash
make redis-start
make run &
make worker &
```

### Run Stage 3 Tests
```bash
pytest -m "stage_3_3 or stage_3_4 or stage_3_5" -v
```

### Run Integration Tests
```bash
pytest -m stage_3_6 --run-integration -v
```

## Key Files Created

```
backend/
├── services/
│   ├── config_generator.py     # Generate job-specific configs
│   ├── error_handler.py        # Error mapping and messages
│   └── progress_parser.py      # Parse pipeline progress
└── workers/
    └── pipeline_worker.py      # Execute real pipeline

tests/
├── test_stage_3_3.py           # Pipeline worker tests
├── test_stage_3_4.py           # Config mapping tests
├── test_stage_3_5.py           # Error handling tests
└── test_stage_3_6_integration.py  # Full integration tests
```

## Completion Tracking

Create `STAGE_3.X_COMPLETED.md` files as each step is finished:

- [ ] Stage 3.1 → `STAGE_3.1_COMPLETED.md`
- [ ] Stage 3.2 → `STAGE_3.2_COMPLETED.md`
- [ ] Stage 3.3 → `STAGE_3.3_COMPLETED.md`
- [ ] Stage 3.4 → `STAGE_3.4_COMPLETED.md`
- [ ] Stage 3.5 → `STAGE_3.5_COMPLETED.md`
- [ ] Stage 3.6 → `STAGE_3.6_COMPLETED.md`

## Notes for AI Agents

1. **Execute steps in order** - each step depends on the previous
2. **Run verification commands** after each step before proceeding
3. **Create COMPLETED.md files** to track progress
4. **Check GPU status** before running pipeline tests
5. **Use `USE_DUMMY_PIPELINE=1`** environment variable to test without real pipeline


