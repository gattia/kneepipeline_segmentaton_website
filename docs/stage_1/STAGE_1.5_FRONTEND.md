# Stage 1.5: Frontend

## Overview

**Goal**: Build the complete web UI for file upload, progress tracking, and download.

**Estimated Time**: ~45 minutes

**Deliverable**: A working frontend served by FastAPI that handles the full user flow.

---

## What This Stage Covers

1. **HTML Structure** - `frontend/index.html`
   - Upload section with FilePond dropzone
   - Configuration panel (email, model selection, NSM options)
   - Processing section with progress bar
   - Complete section with download button
   - Error section
   - Footer with statistics

2. **CSS Styling** - `frontend/css/styles.css`
   - Modern, clean design with CSS variables
   - Responsive layout
   - Form styling, buttons, progress bar, alerts

3. **JavaScript Logic** - `frontend/js/app.js`
   - FilePond initialization
   - Form submission with FormData
   - Status polling every 2 seconds
   - Progress bar updates
   - Download handling
   - Stats display

4. **Static File Serving** - Update `main.py` to serve frontend/

5. **End-to-End Testing** - Full upload → process → download flow in browser

---

## Success Criteria

- [ ] Can access the UI at http://VM_IP:8000/
- [ ] File upload works with drag-drop and file picker
- [ ] Progress bar updates as job processes
- [ ] Download button works when job completes
- [ ] Statistics display in footer
- [ ] Responsive on mobile

---

## Detailed Steps

*(To be expanded)*
