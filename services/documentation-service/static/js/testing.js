/**
 * RegulateAI Testing Dashboard JavaScript
 * 
 * Provides interactive functionality for the web-based testing interface including:
 * - Real-time test execution monitoring
 * - WebSocket/SSE connections for live updates
 * - Test configuration and execution
 * - Test result visualization
 */

class TestingDashboard {
    constructor() {
        this.activeConnections = new Map();
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
        console.log('Testing Dashboard initialized');
    }

    setupEventListeners() {
        // Auto-refresh toggle
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
                this.startAutoRefresh();
            }
        });

        // Form validation
        const testConfigForm = document.getElementById('testConfigForm');
        if (testConfigForm) {
            testConfigForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.executeTests();
            });
        }
    }

    startAutoRefresh() {
        if (this.updateInterval) return;
        
        this.updateInterval = setInterval(() => {
            this.refreshActiveRuns();
        }, 5000); // Refresh every 5 seconds
    }

    stopAutoRefresh() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async refreshActiveRuns() {
        try {
            const response = await fetch('/api/testing/active-runs');
            if (response.ok) {
                const activeRuns = await response.json();
                this.updateActiveRunsDisplay(activeRuns);
            }
        } catch (error) {
            console.error('Failed to refresh active runs:', error);
        }
    }

    updateActiveRunsDisplay(activeRuns) {
        activeRuns.forEach(run => {
            const rowElement = document.getElementById(`run-${run.id}`);
            if (rowElement) {
                this.updateRunRow(rowElement, run);
            }
        });
    }

    updateRunRow(rowElement, run) {
        // Update progress bar
        const progressBar = rowElement.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${run.progress.progress_percent}%`;
            progressBar.textContent = `${run.progress.progress_percent.toFixed(1)}%`;
            progressBar.setAttribute('aria-valuenow', run.progress.progress_percent);
        }

        // Update progress text
        const progressText = rowElement.querySelector('.text-muted');
        if (progressText) {
            progressText.textContent = `${run.progress.completed_tests}/${run.progress.total_tests} tests`;
        }

        // Update status badge
        const statusBadge = rowElement.querySelector('.badge');
        if (statusBadge) {
            statusBadge.textContent = run.status;
            statusBadge.className = `badge bg-${this.getStatusColor(run.status)}`;
        }
    }

    getStatusColor(status) {
        const colors = {
            'Queued': 'secondary',
            'Running': 'primary',
            'Completed': 'success',
            'Failed': 'danger',
            'Cancelled': 'warning',
            'Timeout': 'dark'
        };
        return colors[status] || 'secondary';
    }

    showTestConfigModal() {
        const modal = new bootstrap.Modal(document.getElementById('testConfigModal'));
        modal.show();
    }

    async executeTests() {
        const form = document.getElementById('testConfigForm');
        const formData = new FormData(form);
        
        // Validate form
        if (!this.validateTestConfig(formData)) {
            return;
        }

        // Build test request
        const testRequest = this.buildTestRequest(formData);
        
        try {
            this.showLoadingState(true);
            
            const response = await fetch('/api/testing/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(testRequest)
            });

            if (response.ok) {
                const result = await response.json();
                this.handleTestExecutionSuccess(result);
            } else {
                const error = await response.json();
                this.handleTestExecutionError(error);
            }
        } catch (error) {
            console.error('Test execution failed:', error);
            this.showNotification('Test execution failed', 'error');
        } finally {
            this.showLoadingState(false);
        }
    }

    validateTestConfig(formData) {
        const name = formData.get('name');
        const services = formData.getAll('services');
        const testTypes = formData.getAll('test_types');

        if (!name || name.trim() === '') {
            this.showNotification('Please enter a test name', 'warning');
            return false;
        }

        if (services.length === 0) {
            this.showNotification('Please select at least one service', 'warning');
            return false;
        }

        if (testTypes.length === 0) {
            this.showNotification('Please select at least one test type', 'warning');
            return false;
        }

        return true;
    }

    buildTestRequest(formData) {
        return {
            name: formData.get('name'),
            services: formData.getAll('services'),
            test_types: formData.getAll('test_types'),
            test_filters: null,
            environment: {},
            options: {
                parallel: formData.has('parallel'),
                capture_output: true,
                fail_fast: false,
                verbose: formData.has('verbose'),
                test_threads: parseInt(formData.get('test_threads')) || 4,
                test_timeout: parseInt(formData.get('test_timeout')) || 300
            },
            scheduled_at: null
        };
    }

    handleTestExecutionSuccess(result) {
        this.showNotification(`Test execution started: ${result.run_id}`, 'success');
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('testConfigModal'));
        modal.hide();
        
        // Start monitoring the test run
        this.startTestMonitoring(result.run_id);
        
        // Refresh dashboard
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    handleTestExecutionError(error) {
        this.showNotification(`Test execution failed: ${error.message}`, 'error');
    }

    startTestMonitoring(runId) {
        // Connect to WebSocket for real-time updates
        this.connectWebSocket(runId);
        
        // Also setup SSE as fallback
        this.connectSSE(runId);
    }

    connectWebSocket(runId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/testing/runs/${runId}/ws`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log(`WebSocket connected for test run: ${runId}`);
            this.activeConnections.set(runId, ws);
        };
        
        ws.onmessage = (event) => {
            try {
                const update = JSON.parse(event.data);
                this.handleTestUpdate(update);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        ws.onclose = () => {
            console.log(`WebSocket disconnected for test run: ${runId}`);
            this.activeConnections.delete(runId);
        };
        
        ws.onerror = (error) => {
            console.error(`WebSocket error for test run ${runId}:`, error);
        };
    }

    connectSSE(runId) {
        const sseUrl = `/api/testing/runs/${runId}/sse`;
        const eventSource = new EventSource(sseUrl);
        
        eventSource.onmessage = (event) => {
            try {
                const update = JSON.parse(event.data);
                this.handleTestUpdate(update);
            } catch (error) {
                console.error('Failed to parse SSE message:', error);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error(`SSE error for test run ${runId}:`, error);
            eventSource.close();
        };
        
        // Store reference for cleanup
        this.activeConnections.set(`sse-${runId}`, eventSource);
    }

    handleTestUpdate(update) {
        console.log('Test update received:', update);
        
        switch (update.update_type) {
            case 'StatusChange':
                this.handleStatusChange(update);
                break;
            case 'ProgressUpdate':
                this.handleProgressUpdate(update);
                break;
            case 'LogEntry':
                this.handleLogEntry(update);
                break;
            case 'TestStarted':
                this.handleTestStarted(update);
                break;
            case 'TestCompleted':
                this.handleTestCompleted(update);
                break;
            case 'ServiceStarted':
                this.handleServiceStarted(update);
                break;
            case 'ServiceCompleted':
                this.handleServiceCompleted(update);
                break;
            case 'Error':
                this.handleError(update);
                break;
        }
    }

    handleStatusChange(update) {
        const runId = update.run_id;
        const status = update.data.status;
        
        // Update status in UI
        const statusElements = document.querySelectorAll(`[data-run-id="${runId}"] .badge`);
        statusElements.forEach(element => {
            element.textContent = status;
            element.className = `badge bg-${this.getStatusColor(status)}`;
        });
        
        // Show notification for important status changes
        if (status === 'Completed' || status === 'Failed') {
            this.showNotification(`Test run ${status.toLowerCase()}: ${runId}`, 
                                status === 'Completed' ? 'success' : 'error');
        }
    }

    handleProgressUpdate(update) {
        const runId = update.run_id;
        const progress = update.data;
        
        // Update progress bars
        const progressBars = document.querySelectorAll(`[data-run-id="${runId}"] .progress-bar`);
        progressBars.forEach(bar => {
            bar.style.width = `${progress.progress_percent}%`;
            bar.textContent = `${progress.progress_percent.toFixed(1)}%`;
        });
    }

    handleLogEntry(update) {
        const logEntry = update.data;
        
        // Add to log viewer if open
        const logViewer = document.getElementById('logViewer');
        if (logViewer) {
            this.appendLogEntry(logViewer, logEntry);
        }
    }

    appendLogEntry(logViewer, logEntry) {
        const logLine = document.createElement('div');
        logLine.className = `log-entry log-${logEntry.level.toLowerCase()}`;
        logLine.innerHTML = `
            <span class="log-timestamp">${new Date(logEntry.timestamp).toLocaleTimeString()}</span>
            <span class="log-level badge bg-${this.getLogLevelColor(logEntry.level)}">${logEntry.level}</span>
            <span class="log-message">${this.escapeHtml(logEntry.message)}</span>
        `;
        
        logViewer.appendChild(logLine);
        logViewer.scrollTop = logViewer.scrollHeight;
    }

    getLogLevelColor(level) {
        const colors = {
            'Debug': 'secondary',
            'Info': 'info',
            'Warn': 'warning',
            'Error': 'danger',
            'Fatal': 'dark'
        };
        return colors[level] || 'secondary';
    }

    async viewTestDetails(runId) {
        try {
            const response = await fetch(`/api/testing/runs/${runId}`);
            if (response.ok) {
                const testRun = await response.json();
                this.showTestDetailsModal(testRun);
            } else {
                this.showNotification('Failed to load test details', 'error');
            }
        } catch (error) {
            console.error('Failed to load test details:', error);
            this.showNotification('Failed to load test details', 'error');
        }
    }

    showTestDetailsModal(testRun) {
        const modal = document.getElementById('testDetailsModal');
        const content = document.getElementById('testDetailsContent');
        
        content.innerHTML = this.renderTestDetails(testRun);
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Start real-time monitoring for this test
        if (testRun.status === 'Running') {
            this.startTestMonitoring(testRun.id);
        }
    }

    renderTestDetails(testRun) {
        return `
            <div class="row">
                <div class="col-md-6">
                    <h6>Test Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Name:</strong></td><td>${testRun.request.name}</td></tr>
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-${this.getStatusColor(testRun.status)}">${testRun.status}</span></td></tr>
                        <tr><td><strong>Started:</strong></td><td>${new Date(testRun.started_at).toLocaleString()}</td></tr>
                        <tr><td><strong>Services:</strong></td><td>${testRun.request.services.join(', ')}</td></tr>
                        <tr><td><strong>Test Types:</strong></td><td>${testRun.request.test_types.join(', ')}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Progress</h6>
                    <div class="progress mb-2" style="height: 25px;">
                        <div class="progress-bar" style="width: ${testRun.progress.progress_percent}%">
                            ${testRun.progress.progress_percent.toFixed(1)}%
                        </div>
                    </div>
                    <div class="row text-center">
                        <div class="col-3">
                            <div class="text-success"><strong>${testRun.progress.passed_tests}</strong></div>
                            <small>Passed</small>
                        </div>
                        <div class="col-3">
                            <div class="text-danger"><strong>${testRun.progress.failed_tests}</strong></div>
                            <small>Failed</small>
                        </div>
                        <div class="col-3">
                            <div class="text-warning"><strong>${testRun.progress.skipped_tests}</strong></div>
                            <small>Skipped</small>
                        </div>
                        <div class="col-3">
                            <div class="text-info"><strong>${testRun.progress.total_tests}</strong></div>
                            <small>Total</small>
                        </div>
                    </div>
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="col-12">
                    <h6>Real-time Logs</h6>
                    <div id="logViewer" class="log-viewer" style="height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">
                        ${testRun.logs.map(log => `
                            <div class="log-entry log-${log.level.toLowerCase()}">
                                <span class="log-timestamp">${new Date(log.timestamp).toLocaleTimeString()}</span>
                                <span class="log-level badge bg-${this.getLogLevelColor(log.level)}">${log.level}</span>
                                <span class="log-message">${this.escapeHtml(log.message)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    async cancelTestRun(runId) {
        if (!confirm('Are you sure you want to cancel this test run?')) {
            return;
        }

        try {
            const response = await fetch(`/api/testing/runs/${runId}/cancel`, {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Test run cancelled successfully', 'success');
                this.refreshActiveRuns();
            } else {
                this.showNotification('Failed to cancel test run', 'error');
            }
        } catch (error) {
            console.error('Failed to cancel test run:', error);
            this.showNotification('Failed to cancel test run', 'error');
        }
    }

    showLoadingState(loading) {
        const buttons = document.querySelectorAll('.btn-primary');
        buttons.forEach(button => {
            if (loading) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
            } else {
                button.disabled = false;
                button.innerHTML = button.getAttribute('data-original-text') || button.innerHTML;
            }
        });
    }

    showNotification(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        // Add to toast container
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }

        container.appendChild(toast);

        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // Remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    refreshDashboard() {
        window.location.reload();
    }
}

// Global functions for template usage
function showTestConfigModal() {
    dashboard.showTestConfigModal();
}

function executeTests() {
    dashboard.executeTests();
}

function viewTestDetails(runId) {
    dashboard.viewTestDetails(runId);
}

function cancelTestRun(runId) {
    dashboard.cancelTestRun(runId);
}

function refreshDashboard() {
    dashboard.refreshDashboard();
}

function viewTestResults(testId) {
    window.location.href = `/testing/results/${testId}`;
}

function rerunTest(testId) {
    // Implementation for rerunning a test
    console.log('Rerun test:', testId);
}

function showScheduleModal() {
    // Implementation for test scheduling
    console.log('Show schedule modal');
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TestingDashboard();
});
