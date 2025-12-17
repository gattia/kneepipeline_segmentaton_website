# Stage 1.5: Frontend

## Overview

**Goal**: Build the complete web UI for file upload, progress tracking, and download.

**Estimated Time**: ~45 minutes

**Deliverable**: A working frontend served by FastAPI that handles the full user flow.

---

## What This Stage Creates

### Files to Create

```
frontend/
├── index.html              # Main HTML page (REPLACE existing placeholder)
├── css/
│   └── styles.css          # NEW: All styling
└── js/
    └── app.js              # NEW: Upload logic, polling, UI state
```

### Prerequisites

Before starting, verify:

1. **All previous stages pass**:
   ```bash
   make verify
   ```

2. **Redis is running**:
   ```bash
   make redis-ping
   ```

3. **Backend API is functional**:
   ```bash
   curl http://localhost:8000/health | jq
   curl http://localhost:8000/stats | jq
   ```

---

## Detailed Implementation

### Step 1: Create CSS Directory and Styles

**Create directory**: `frontend/css/`

**Create file**: `frontend/css/styles.css`

This file contains all the styling for the application. Key sections:

| Section | Purpose |
|---------|---------|
| CSS Variables (`:root`) | Colors, border-radius, reusable values |
| Base Styles | Body, container, typography |
| Header | Title and subtitle |
| Sections | Cards with background, shadow, padding |
| Upload Area | FilePond container |
| Config Panel | Form groups, inputs, checkboxes, radio buttons |
| Buttons | Primary, secondary, disabled states |
| Alerts | Warning, info, error styles |
| Progress | Progress bar container, fill animation, indeterminate state |
| Queue Info | Queue position display |
| Complete/Error Sections | Success and error states |
| Footer | Statistics and disclaimer |
| Responsive | Mobile breakpoints |

**Full CSS code:**

```css
/* Base Styles */
:root {
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --bg-color: #f8fafc;
    --card-bg: #ffffff;
    --text-color: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --border-radius: 12px;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 680px;
    margin: 0 auto;
    padding: 2rem 1rem;
}

/* Header */
header {
    text-align: center;
    margin-bottom: 2rem;
}

header h1 {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
}

header .subtitle {
    color: var(--text-muted);
}

/* Sections */
.section {
    background: var(--card-bg);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.hidden {
    display: none !important;
}

/* Upload Area */
.upload-area {
    margin-bottom: 1.5rem;
}

.filepond--root {
    font-family: inherit;
}

/* Config Panel */
.config-panel {
    border-top: 1px solid var(--border-color);
    padding-top: 1.5rem;
    margin-bottom: 1.5rem;
}

.config-panel h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-group select,
.form-group input[type="email"] {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 1rem;
}

.form-group input[type="email"]:focus,
.form-group select:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Invalid input styling */
.form-group input[type="email"]:invalid:not(:placeholder-shown) {
    border-color: var(--error-color);
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.checkbox-label input {
    width: 18px;
    height: 18px;
}

.radio-group {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.radio-group label {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-weight: normal;
    cursor: pointer;
}

.help-text {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s, opacity 0.2s;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn.primary {
    background: var(--primary-color);
    color: white;
    width: 100%;
}

.btn.primary:hover:not(:disabled) {
    background: var(--primary-hover);
}

.btn.secondary {
    background: var(--border-color);
    color: var(--text-color);
}

.btn.secondary:hover {
    background: #d1d5db;
}

.btn.large {
    padding: 1rem 2rem;
    font-size: 1.125rem;
}

/* Alerts */
.alert {
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

.alert.warning {
    background: #fef3c7;
    color: #92400e;
}

.alert.info {
    background: #dbeafe;
    color: #1e40af;
}

.alert.error {
    background: #fee2e2;
    color: #991b1b;
}

/* Progress */
.progress-container {
    margin: 1.5rem 0;
}

.progress-bar {
    height: 24px;
    background: var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: var(--primary-color);
    transition: width 0.3s ease;
    width: 0%;
}

/* Indeterminate progress animation for queue waiting */
.progress-fill.indeterminate {
    width: 30%;
    animation: indeterminate 1.5s infinite ease-in-out;
}

@keyframes indeterminate {
    0% {
        transform: translateX(-100%);
    }
    100% {
        transform: translateX(400%);
    }
}

.progress-text {
    text-align: center;
    margin-top: 0.5rem;
    color: var(--text-muted);
}

/* Queue Info */
.queue-info {
    text-align: center;
    margin: 1rem 0;
}

.queue-info p {
    margin: 0.25rem 0;
}

/* Complete Section */
.complete-info {
    text-align: center;
}

.complete-info h2 {
    color: var(--success-color);
    margin-bottom: 1rem;
}

.complete-info p {
    margin: 0.5rem 0;
}

#download-btn {
    margin: 1.5rem 0;
}

#new-upload-btn {
    margin-top: 1rem;
}

/* Error Section */
.error-info {
    text-align: center;
}

.error-info h2 {
    color: var(--error-color);
    margin-bottom: 1rem;
}

#error-message {
    margin-bottom: 1.5rem;
    color: var(--text-muted);
}

/* Footer */
footer {
    text-align: center;
    padding: 1rem;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.stats {
    margin-bottom: 0.5rem;
}

.disclaimer {
    font-size: 0.85rem;
}

/* Responsive */
@media (max-width: 480px) {
    .container {
        padding: 1rem;
    }
    
    .radio-group {
        flex-direction: column;
        gap: 0.5rem;
    }
}
```

---

### Step 2: Create JavaScript Directory and App Logic

**Create directory**: `frontend/js/`

**Create file**: `frontend/js/app.js`

This file handles all frontend interactivity:

| Component | Purpose |
|-----------|---------|
| `state` object | Tracks current jobId, filename, poll interval, poll failures |
| `elements` object | Cached DOM element references |
| `initFilePond()` | Initializes drag-drop file upload with client-side validation |
| `showSection()` | Toggles visibility of upload/processing/complete/error sections |
| `validateEmail()` | Validates email format before upload |
| `uploadFile()` | Submits form data to `/upload` endpoint |
| `startPolling()` / `pollStatus()` | Polls `/status/{job_id}` every 2 seconds with failure handling |
| `showComplete()` | Displays download button when job completes |
| `showError()` | Displays error message |
| `resetToUpload()` | Resets UI to initial state |
| `loadStats()` | Fetches and displays footer statistics |

**Full JavaScript code:**

```javascript
// State management
const state = {
    jobId: null,
    filename: null,
    pollInterval: null,
    pollFailures: 0,        // Track consecutive poll failures
    maxPollFailures: 5,     // Show warning after this many failures
};

// DOM Elements
const elements = {
    // Sections
    uploadSection: document.getElementById('upload-section'),
    processingSection: document.getElementById('processing-section'),
    completeSection: document.getElementById('complete-section'),
    errorSection: document.getElementById('error-section'),
    
    // Upload
    fileInput: document.getElementById('file-input'),
    submitBtn: document.getElementById('submit-btn'),
    emailInput: document.getElementById('email-input'),
    segModel: document.getElementById('seg-model'),
    performNsm: document.getElementById('perform-nsm'),
    nsmOptions: document.getElementById('nsm-options'),
    retainResults: document.getElementById('retain-results'),
    
    // Processing
    processingFilename: document.getElementById('processing-filename'),
    queuePosition: document.getElementById('queue-position'),
    estimatedWait: document.getElementById('estimated-wait'),
    progressFill: document.getElementById('progress-fill'),
    progressPercent: document.getElementById('progress-percent'),
    stepName: document.getElementById('step-name'),
    cancelBtn: document.getElementById('cancel-btn'),
    connectionWarning: document.getElementById('connection-warning'),
    
    // Complete
    completeFilename: document.getElementById('complete-filename'),
    processingDuration: document.getElementById('processing-duration'),
    downloadBtn: document.getElementById('download-btn'),
    resultSize: document.getElementById('result-size'),
    newUploadBtn: document.getElementById('new-upload-btn'),
    
    // Error
    errorMessage: document.getElementById('error-message'),
    retryBtn: document.getElementById('retry-btn'),
    
    // Stats
    totalProcessed: document.getElementById('total-processed'),
    uniqueUsers: document.getElementById('unique-users'),
    avgTime: document.getElementById('avg-time'),
};

// Allowed file extensions (for client-side validation)
const ALLOWED_EXTENSIONS = ['.zip', '.nii', '.nii.gz', '.nrrd', '.dcm'];

// Initialize FilePond
let pond = null;

function initFilePond() {
    pond = FilePond.create(elements.fileInput, {
        allowMultiple: false,
        maxFileSize: '600MB',
        // Client-side file type validation for better UX
        beforeAddFile: (item) => {
            const filename = item.file.name.toLowerCase();
            const isValid = ALLOWED_EXTENSIONS.some(ext => filename.endsWith(ext));
            if (!isValid) {
                alert(`Invalid file type. Accepted formats: ${ALLOWED_EXTENSIONS.join(', ')}`);
                return false;
            }
            return true;
        },
        labelIdle: '📁 Drop your MRI data here or <span class="filepond--label-action">browse</span><br><small>Accepted: .zip, .nii.gz, .nrrd, .dcm</small>',
        credits: false,
    });
    
    pond.on('addfile', (error, file) => {
        if (!error) {
            elements.submitBtn.disabled = false;
        }
    });
    
    pond.on('removefile', () => {
        elements.submitBtn.disabled = true;
    });
}

// Section visibility
function showSection(sectionId) {
    ['upload', 'processing', 'complete', 'error'].forEach(id => {
        const section = document.getElementById(`${id}-section`);
        if (section) {
            section.classList.toggle('hidden', id !== sectionId);
        }
    });
}

// Email validation
function validateEmail(email) {
    if (!email) return true; // Email is optional
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Format time
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds} seconds`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${minutes} min ${secs} sec` : `${minutes} minutes`;
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Upload file
async function uploadFile() {
    const files = pond.getFiles();
    if (files.length === 0) return;
    
    // Validate email if provided
    const email = elements.emailInput.value.trim();
    if (email && !validateEmail(email)) {
        alert('Please enter a valid email address or leave it empty.');
        elements.emailInput.focus();
        return;
    }
    
    const file = files[0].file;
    state.filename = file.name;
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Include email if provided
    if (email) {
        formData.append('email', email);
    }
    
    formData.append('segmentation_model', elements.segModel.value);
    formData.append('perform_nsm', elements.performNsm.checked);
    formData.append('nsm_type', document.querySelector('input[name="nsm-type"]:checked').value);
    formData.append('retain_results', elements.retainResults.checked);
    
    try {
        elements.submitBtn.disabled = true;
        elements.submitBtn.textContent = 'Uploading...';
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        state.jobId = data.job_id;
        state.pollFailures = 0; // Reset failure counter
        
        // Show processing section
        elements.processingFilename.textContent = state.filename;
        elements.queuePosition.textContent = `#${data.queue_position}`;
        elements.estimatedWait.textContent = `~${formatDuration(data.estimated_wait_seconds)}`;
        
        // Show indeterminate progress while queued
        elements.progressFill.classList.add('indeterminate');
        
        showSection('processing');
        startPolling();
        
    } catch (error) {
        showError(error.message);
    } finally {
        elements.submitBtn.disabled = false;
        elements.submitBtn.textContent = 'Process Data';
    }
}

// Poll for status
function startPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
    }
    
    state.pollFailures = 0;
    hideConnectionWarning();
    
    pollStatus(); // Immediate first poll
    state.pollInterval = setInterval(pollStatus, 2000); // Every 2 seconds
}

async function pollStatus() {
    if (!state.jobId) return;
    
    try {
        const response = await fetch(`/status/${state.jobId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get status');
        }
        
        const data = await response.json();
        
        // Reset failure counter on success
        state.pollFailures = 0;
        hideConnectionWarning();
        
        switch (data.status) {
            case 'queued':
                elements.queuePosition.textContent = `#${data.queue_position}`;
                elements.estimatedWait.textContent = `~${formatDuration(data.estimated_wait_seconds)}`;
                // Keep indeterminate animation while queued
                elements.progressFill.classList.add('indeterminate');
                elements.progressPercent.textContent = 'Queued';
                elements.stepName.textContent = 'Waiting in queue...';
                break;
                
            case 'processing':
                // Switch to determinate progress
                elements.progressFill.classList.remove('indeterminate');
                elements.queuePosition.textContent = 'Processing';
                elements.estimatedWait.textContent = formatDuration(data.estimated_remaining_seconds);
                elements.progressFill.style.width = `${data.progress_percent}%`;
                elements.progressPercent.textContent = `${data.progress_percent}%`;
                elements.stepName.textContent = `Step ${data.current_step}/${data.total_steps}: ${data.step_name}`;
                break;
                
            case 'complete':
                stopPolling();
                showComplete(data);
                break;
                
            case 'error':
                stopPolling();
                showError(data.error_message);
                break;
        }
        
    } catch (error) {
        console.error('Polling error:', error);
        state.pollFailures++;
        
        // Show warning after multiple failures
        if (state.pollFailures >= state.maxPollFailures) {
            showConnectionWarning();
        }
        
        // Don't stop polling - keep trying (server might recover)
    }
}

function stopPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
}

// Connection warning helpers
function showConnectionWarning() {
    if (elements.connectionWarning) {
        elements.connectionWarning.classList.remove('hidden');
    }
}

function hideConnectionWarning() {
    if (elements.connectionWarning) {
        elements.connectionWarning.classList.add('hidden');
    }
}

// Show complete
function showComplete(data) {
    elements.progressFill.classList.remove('indeterminate');
    elements.completeFilename.textContent = state.filename;
    elements.processingDuration.textContent = formatDuration(data.processing_time_seconds);
    elements.resultSize.textContent = formatSize(data.result_size_bytes);
    elements.downloadBtn.onclick = () => {
        window.location.href = data.download_url;
    };
    showSection('complete');
}

// Show error
function showError(message) {
    elements.progressFill.classList.remove('indeterminate');
    elements.errorMessage.textContent = message;
    showSection('error');
}

// Reset to upload
function resetToUpload() {
    state.jobId = null;
    state.filename = null;
    state.pollFailures = 0;
    stopPolling();
    pond.removeFiles();
    elements.submitBtn.disabled = true;
    elements.progressFill.classList.remove('indeterminate');
    elements.progressFill.style.width = '0%';
    hideConnectionWarning();
    showSection('upload');
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch('/stats');
        if (response.ok) {
            const data = await response.json();
            elements.totalProcessed.textContent = data.total_jobs_processed.toLocaleString();
            elements.uniqueUsers.textContent = data.unique_users.toLocaleString();
            elements.avgTime.textContent = (data.average_processing_time_seconds / 60).toFixed(1);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initFilePond();
    loadStats();
    
    // Button handlers
    elements.submitBtn.addEventListener('click', uploadFile);
    elements.newUploadBtn.addEventListener('click', resetToUpload);
    elements.retryBtn.addEventListener('click', resetToUpload);
    
    // Toggle NSM options visibility
    elements.performNsm.addEventListener('change', (e) => {
        elements.nsmOptions.classList.toggle('hidden', !e.target.checked);
    });
    
    // Cancel button (placeholder for future implementation)
    elements.cancelBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to cancel processing?')) {
            // TODO (Phase 2): Call cancel API endpoint when implemented
            resetToUpload();
        }
    });
    
    // Refresh stats periodically
    setInterval(loadStats, 60000); // Every minute
});
```

---

### Step 3: Replace index.html

**Replace file**: `frontend/index.html`

Replace the existing placeholder with the complete HTML structure:

| Section | Element IDs | Purpose |
|---------|-------------|---------|
| Upload Section | `upload-section`, `file-input`, `submit-btn` | File selection and configuration |
| Processing Section | `processing-section`, `progress-fill`, `step-name`, `connection-warning` | Progress display during processing |
| Complete Section | `complete-section`, `download-btn` | Download results |
| Error Section | `error-section`, `error-message` | Error display |
| Footer | `total-processed`, `unique-users`, `avg-time` | Statistics |

**Full HTML code:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knee MRI Analysis Pipeline</title>
    <link rel="stylesheet" href="/css/styles.css">
    <!-- FilePond CSS (pinned version for reproducibility) -->
    <link href="https://unpkg.com/filepond@4.31.4/dist/filepond.css" rel="stylesheet" />
</head>
<body>
    <div class="container">
        <header>
            <h1>🦴 Knee MRI Analysis Pipeline</h1>
            <p class="subtitle">Automated segmentation and analysis of knee MRI data</p>
        </header>

        <!-- Upload Section -->
        <section id="upload-section" class="section">
            <div class="upload-area">
                <input type="file" id="file-input">
            </div>
            
            <div class="config-panel">
                <h3>Configuration</h3>
                
                <div class="form-group">
                    <label for="email-input">Email (optional):</label>
                    <input type="email" id="email-input" placeholder="your@email.com">
                    <p class="help-text">
                        For usage tracking and to receive your download link via email.
                    </p>
                </div>
                
                <div class="form-group">
                    <label for="seg-model">Segmentation Model:</label>
                    <select id="seg-model">
                        <option value="nnunet_fullres" selected>nnU-Net FullRes (recommended)</option>
                        <option value="nnunet_cascade">nnU-Net Cascade</option>
                        <option value="goyal_sagittal">DOSMA Sagittal</option>
                        <option value="goyal_coronal">DOSMA Coronal</option>
                        <option value="goyal_axial">DOSMA Axial</option>
                        <option value="staple">DOSMA STAPLE (ensemble)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="perform-nsm" checked>
                        Perform Shape Modeling (NSM)
                    </label>
                </div>
                
                <div class="form-group" id="nsm-options">
                    <label>NSM Type:</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="nsm-type" value="bone_and_cart" checked>
                            Bone + Cartilage
                        </label>
                        <label>
                            <input type="radio" name="nsm-type" value="bone_only">
                            Bone Only
                        </label>
                        <label>
                            <input type="radio" name="nsm-type" value="both">
                            Both
                        </label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="retain-results" checked>
                        Allow anonymized results to be retained for research
                    </label>
                    <p class="help-text">
                        Only derived data (segmentations, meshes, metrics) will be retained. 
                        No original MRI images are stored.
                    </p>
                </div>
            </div>
            
            <button id="submit-btn" class="btn primary" disabled>
                Process Data
            </button>
        </section>

        <!-- Processing Section -->
        <section id="processing-section" class="section hidden">
            <div class="processing-info">
                <h2>Processing: <span id="processing-filename"></span></h2>
                
                <div class="alert warning">
                    ⚠️ Please keep this page open until processing completes.
                </div>
                
                <!-- Connection warning (shown after multiple poll failures) -->
                <div id="connection-warning" class="alert error hidden">
                    ⚠️ Connection issues detected. Retrying...
                </div>
                
                <div class="queue-info">
                    <p>Queue Position: <strong id="queue-position">#1</strong></p>
                    <p>Estimated Wait: <strong id="estimated-wait">~4 minutes</strong></p>
                </div>
                
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <p class="progress-text">
                        <span id="progress-percent">0%</span> - 
                        <span id="step-name">Initializing...</span>
                    </p>
                </div>
                
                <button id="cancel-btn" class="btn secondary">Cancel</button>
            </div>
        </section>

        <!-- Complete Section -->
        <section id="complete-section" class="section hidden">
            <div class="complete-info">
                <h2>✅ Processing Complete!</h2>
                
                <p>File: <strong id="complete-filename"></strong></p>
                <p>Duration: <strong id="processing-duration"></strong></p>
                
                <button id="download-btn" class="btn primary large">
                    ⬇️ Download Results (<span id="result-size"></span>)
                </button>
                
                <div class="alert info">
                    ⏰ Download available for 24 hours.<br>
                    ⚠️ Do not reload this page until you have downloaded your results.
                </div>
                
                <button id="new-upload-btn" class="btn secondary">
                    Process Another
                </button>
            </div>
        </section>

        <!-- Error Section -->
        <section id="error-section" class="section hidden">
            <div class="error-info">
                <h2>❌ Processing Error</h2>
                <p id="error-message"></p>
                <button id="retry-btn" class="btn primary">Try Again</button>
            </div>
        </section>

        <!-- Footer with Stats -->
        <footer>
            <div class="stats">
                📊 <span id="total-processed">0</span> images processed | 
                <span id="unique-users">0</span> users |
                Avg time: <span id="avg-time">0</span> min
            </div>
            <div class="disclaimer">
                ⚠️ Research use only. Not for clinical diagnosis.
            </div>
        </footer>
    </div>

    <!-- FilePond JS (pinned version for reproducibility) -->
    <script src="https://unpkg.com/filepond@4.31.4/dist/filepond.js"></script>
    <script src="/js/app.js"></script>
</body>
</html>
```

---

## Verification

### Automated Tests

There are no automated tests for the frontend since it's vanilla JavaScript tested in the browser. The key verification is manual testing.

### Manual Testing Procedure

#### Test 1: Page Loads Correctly

```bash
# Terminal 1: Start Redis (if not running)
make redis-start

# Terminal 2: Start Celery worker
make worker

# Terminal 3: Start FastAPI server
make run
```

Open http://localhost:8000 in browser. Verify:

- [ ] Header displays "🦴 Knee MRI Analysis Pipeline"
- [ ] FilePond dropzone displays with "Drop your MRI data here"
- [ ] Configuration panel shows all options (email, model, NSM, retain)
- [ ] "Process Data" button is disabled (no file selected)
- [ ] Footer shows statistics (may be 0)
- [ ] Disclaimer shows "Research use only"

#### Test 2: File Upload Flow

1. Create a test file:
   ```bash
   python -c "
   import SimpleITK as sitk
   img = sitk.Image([16,16,16], sitk.sitkInt16)
   sitk.WriteImage(img, 'test_input.nii.gz')
   print('Created test_input.nii.gz')
   "
   ```

2. Drag the file onto the dropzone (or click to browse)
3. Verify:
   - [ ] File appears in dropzone
   - [ ] "Process Data" button becomes enabled

4. Click "Process Data"
5. Verify:
   - [ ] Button shows "Uploading..."
   - [ ] Transitions to Processing section
   - [ ] Filename displays correctly
   - [ ] Queue position shows (#1, #2, etc.)
   - [ ] Progress bar shows indeterminate animation while queued
   - [ ] Step name shows "Waiting in queue..."

#### Test 3: Processing Progress

Once processing starts. Verify:

- [ ] Progress bar switches from indeterminate to determinate
- [ ] Progress percentage updates
- [ ] Step name updates (e.g., "Step 1/4: Validating input")

#### Test 4: Processing Complete

Wait for processing to complete (dummy worker takes ~7 seconds with delays, ~1 second without). Verify:

- [ ] Transitions to Complete section
- [ ] Shows "✅ Processing Complete!"
- [ ] Shows file name and duration
- [ ] Download button shows file size
- [ ] "Process Another" button visible

#### Test 5: Download Works

1. Click "⬇️ Download Results"
2. Verify:
   - [ ] Browser downloads a `.zip` file
   - [ ] Zip contains `dummy_segmentation.nii.gz`, `results.json`, `results.csv`

#### Test 6: Process Another

1. Click "Process Another"
2. Verify:
   - [ ] Returns to Upload section
   - [ ] Dropzone is cleared
   - [ ] "Process Data" button is disabled

#### Test 7: Client-Side File Validation

1. Try to upload an invalid file (e.g., `.txt` or `.pdf` file)
2. Verify:
   - [ ] Alert shows "Invalid file type" message
   - [ ] File is rejected before upload

#### Test 8: Email Validation

1. Enter an invalid email (e.g., "notanemail")
2. Click "Process Data"
3. Verify:
   - [ ] Alert shows "Please enter a valid email address"
   - [ ] Upload does not proceed

#### Test 9: NSM Options Toggle

1. Uncheck "Perform Shape Modeling (NSM)"
2. Verify:
   - [ ] NSM Type radio buttons are hidden

3. Re-check the checkbox
4. Verify:
   - [ ] NSM Type radio buttons reappear

#### Test 10: Connection Warning

1. Start a processing job
2. Stop the FastAPI server (Ctrl+C)
3. Wait ~10 seconds (5 poll failures)
4. Verify:
   - [ ] Connection warning appears: "Connection issues detected. Retrying..."
5. Restart the server
6. Verify:
   - [ ] Warning disappears once polling succeeds

#### Test 11: Responsive Design

1. Open browser developer tools (F12)
2. Toggle device toolbar (mobile view)
3. Verify:
   - [ ] Layout adapts to narrow screens
   - [ ] Radio buttons stack vertically on mobile
   - [ ] All content is readable

---

## Success Criteria

All of these must be true:

- [ ] Frontend loads at http://localhost:8000/
- [ ] FilePond drag-drop file upload works
- [ ] Client-side file type validation rejects invalid files
- [ ] Email validation works (if email provided)
- [ ] Configuration options (email, model, NSM, retain) are functional
- [ ] Upload submits to `/upload` endpoint correctly
- [ ] Processing section shows queue position and progress
- [ ] Indeterminate progress animation shows while queued
- [ ] Determinate progress bar updates during processing
- [ ] Connection warning appears after multiple poll failures
- [ ] Complete section shows download button
- [ ] Download button downloads the results zip
- [ ] Error handling displays errors appropriately
- [ ] Footer statistics load from `/stats` endpoint
- [ ] Layout is responsive on mobile

---

## Files Summary

| File | Action | Lines |
|------|--------|-------|
| `frontend/css/styles.css` | CREATE | ~270 |
| `frontend/js/app.js` | CREATE | ~250 |
| `frontend/index.html` | REPLACE | ~130 |

**Total**: 3 files, ~650 lines of code

---

## Notes for Implementation

### CDN Dependencies

The frontend uses FilePond from unpkg CDN with **pinned versions** for reproducibility:
- CSS: `https://unpkg.com/filepond@4.31.4/dist/filepond.css`
- JS: `https://unpkg.com/filepond@4.31.4/dist/filepond.js`

No npm install or build step required.

> **Note**: The version `4.31.4` is the latest stable version as of this writing. Update to newer versions after testing if needed.

### Static File Serving

The `backend/main.py` already mounts the frontend directory:

```python
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
```

The `html=True` parameter ensures `index.html` is served for the root path.

### API Routes

The frontend calls these API endpoints (all already implemented):

| Endpoint | Method | When Called |
|----------|--------|-------------|
| `/upload` | POST | On "Process Data" click |
| `/status/{job_id}` | GET | Every 2 seconds during processing |
| `/download/{job_id}` | GET | On "Download Results" click |
| `/stats` | GET | On page load and every 60 seconds |

### Browser Compatibility

The code uses modern JavaScript features:
- `async/await` - supported in all modern browsers
- `fetch` API - supported in all modern browsers
- CSS variables - supported in all modern browsers
- CSS animations - supported in all modern browsers
- Arrow functions - supported in all modern browsers

No transpilation or polyfills needed.

### Deferred to Phase 2

The following features are intentionally deferred:

| Feature | Reason |
|---------|--------|
| localStorage persistence | Allows resuming after browser close - added complexity |
| Cancel API endpoint | Requires backend changes to cancel Celery tasks |
| Email notifications | Requires email service integration |

---

## Next Steps After Stage 1.5

After completing Stage 1.5, Stage 1 is complete! The MVP is functional:

1. **End-to-End Testing**: Perform full upload → process → download flow
2. **Create Stage 1 Completion Document**: Document what was built
3. **Plan Phase 2**: Progress refinements, time estimates, localStorage persistence

Optional improvements for Phase 2:
- Session persistence via localStorage (resume after browser close)
- Rolling time estimates based on job history
- Email notifications when processing completes
- Cancel API endpoint for stopping jobs
