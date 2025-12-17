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
