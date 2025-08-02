/**
 * RegulateAI Advanced Test Analytics JavaScript
 * 
 * Provides advanced testing functionality including:
 * - Coverage analytics visualization
 * - Performance metrics tracking
 * - Chaos testing controls
 * - Fault injection management
 * - Flaky test detection
 */

class AdvancedTestAnalytics {
    constructor() {
        this.coverageChart = null;
        this.performanceChart = null;
        this.init();
    }

    init() {
        this.setupCharts();
        this.setupEventListeners();
        this.loadFlakyTests();
        console.log('Advanced Test Analytics initialized');
    }

    setupCharts() {
        this.setupCoverageChart();
        this.setupPerformanceChart();
    }

    setupCoverageChart() {
        const ctx = document.getElementById('coverageChart').getContext('2d');
        this.coverageChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Line Coverage', 'Branch Coverage', 'Function Coverage', 'Statement Coverage'],
                datasets: [{
                    data: [85.2, 78.9, 92.1, 83.7],
                    backgroundColor: [
                        '#28a745',
                        '#17a2b8',
                        '#ffc107',
                        '#007bff'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    setupPerformanceChart() {
        const ctx = document.getElementById('performanceChart').getContext('2d');
        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['1h ago', '45m ago', '30m ago', '15m ago', 'Now'],
                datasets: [{
                    label: 'Test Execution Time (s)',
                    data: [2.8, 2.5, 2.3, 2.1, 2.3],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Memory Usage (MB)',
                    data: [280, 265, 256, 245, 256],
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Execution Time (s)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Memory Usage (MB)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    setupEventListeners() {
        // Injection rate slider
        const injectionRateSlider = document.getElementById('injectionRate');
        const injectionRateValue = document.getElementById('injectionRateValue');
        
        if (injectionRateSlider && injectionRateValue) {
            injectionRateSlider.addEventListener('input', (e) => {
                injectionRateValue.textContent = e.target.value;
            });
        }

        // Auto-refresh charts every 30 seconds
        setInterval(() => {
            this.refreshCharts();
        }, 30000);
    }

    async refreshCharts() {
        try {
            // Refresh coverage data
            const coverageResponse = await fetch('/api/testing/coverage/latest');
            if (coverageResponse.ok) {
                const coverageData = await coverageResponse.json();
                this.updateCoverageChart(coverageData);
            }

            // Refresh performance data
            const performanceResponse = await fetch('/api/testing/performance/latest');
            if (performanceResponse.ok) {
                const performanceData = await performanceResponse.json();
                this.updatePerformanceChart(performanceData);
            }
        } catch (error) {
            console.error('Failed to refresh charts:', error);
        }
    }

    updateCoverageChart(data) {
        if (this.coverageChart && data.coverage_details) {
            const coverage = data.coverage_details;
            this.coverageChart.data.datasets[0].data = [
                coverage.line_coverage,
                coverage.branch_coverage,
                coverage.function_coverage,
                coverage.statement_coverage
            ];
            this.coverageChart.update();
        }
    }

    updatePerformanceChart(data) {
        if (this.performanceChart && data) {
            // Add new data point and remove oldest
            const timeLabel = new Date().toLocaleTimeString();
            this.performanceChart.data.labels.push(timeLabel);
            this.performanceChart.data.labels.shift();
            
            this.performanceChart.data.datasets[0].data.push(data.avg_execution_time_ms / 1000);
            this.performanceChart.data.datasets[0].data.shift();
            
            this.performanceChart.data.datasets[1].data.push(data.memory_usage_mb);
            this.performanceChart.data.datasets[1].data.shift();
            
            this.performanceChart.update();
        }
    }

    async loadFlakyTests() {
        try {
            const services = ['aml', 'compliance', 'risk-management'];
            const flakyTestsTable = document.getElementById('flakyTestsTable').getElementsByTagName('tbody')[0];
            
            for (const service of services) {
                const response = await fetch(`/api/testing/flaky-tests/${service}`);
                if (response.ok) {
                    const flakyTests = await response.json();
                    this.displayFlakyTests(flakyTestsTable, flakyTests);
                }
            }
        } catch (error) {
            console.error('Failed to load flaky tests:', error);
        }
    }

    displayFlakyTests(tableBody, flakyTests) {
        flakyTests.forEach(test => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td><strong>${test.test_name}</strong></td>
                <td>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar ${this.getSuccessRateColor(test.success_rate)}" 
                             style="width: ${test.success_rate}%">
                            ${test.success_rate.toFixed(1)}%
                        </div>
                    </div>
                </td>
                <td>${test.total_runs}</td>
                <td><span class="text-danger">${test.failed_runs}</span></td>
                <td>
                    <span class="badge ${this.getFlakinessScoreColor(test.flakiness_score)}">
                        ${test.flakiness_score.toFixed(1)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="analyzeTest('${test.test_name}')">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-warning" onclick="quarantineTest('${test.test_name}')">
                        <i class="fas fa-ban"></i>
                    </button>
                </td>
            `;
        });
    }

    getSuccessRateColor(rate) {
        if (rate >= 80) return 'bg-success';
        if (rate >= 60) return 'bg-warning';
        return 'bg-danger';
    }

    getFlakinessScoreColor(score) {
        if (score >= 80) return 'bg-danger';
        if (score >= 60) return 'bg-warning';
        return 'bg-success';
    }

    async startChaosTest() {
        const chaosType = document.getElementById('chaosType').value;
        const targetServices = Array.from(document.querySelectorAll('input[id^="chaos_"]:checked'))
            .map(input => input.value);

        if (targetServices.length === 0) {
            this.showNotification('Please select at least one target service', 'warning');
            return;
        }

        const chaosConfig = {
            id: this.generateUUID(),
            name: `Chaos Test - ${chaosType}`,
            target_services: targetServices,
            experiments: [{
                id: this.generateUUID(),
                name: `${chaosType} Experiment`,
                experiment_type: chaosType,
                targets: targetServices,
                parameters: this.getChaosParameters(chaosType),
                expected_impact: 'Medium',
                rollback_strategy: {
                    auto_rollback: true,
                    rollback_timeout_seconds: 300,
                    rollback_commands: [],
                    health_check_endpoint: null
                }
            }],
            duration_seconds: 300,
            failure_tolerance: 0.1,
            expected_recovery_time_seconds: 120
        };

        try {
            const response = await fetch('/api/testing/chaos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(chaosConfig)
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(`Chaos test started: ${result.run_id}`, 'success');
                this.monitorChaosTest(result.run_id);
            } else {
                this.showNotification('Failed to start chaos test', 'error');
            }
        } catch (error) {
            console.error('Chaos test failed:', error);
            this.showNotification('Chaos test failed', 'error');
        }
    }

    async startFaultInjection() {
        const faultType = document.getElementById('faultType').value;
        const injectionRate = document.getElementById('injectionRate').value / 100;

        const faultConfig = {
            id: this.generateUUID(),
            name: `Fault Injection - ${faultType}`,
            target_services: ['aml', 'compliance'],
            fault_types: [this.buildFaultType(faultType)],
            injection_rate: injectionRate,
            duration_seconds: 300,
            conditions: []
        };

        try {
            const response = await fetch('/api/testing/fault-injection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(faultConfig)
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(`Fault injection started: ${result.run_id}`, 'success');
                this.monitorFaultInjection(result.run_id);
            } else {
                this.showNotification('Failed to start fault injection', 'error');
            }
        } catch (error) {
            console.error('Fault injection failed:', error);
            this.showNotification('Fault injection failed', 'error');
        }
    }

    getChaosParameters(chaosType) {
        const parameters = {};
        switch (chaosType) {
            case 'NetworkLatency':
                parameters.latency_ms = 100;
                break;
            case 'CpuStress':
                parameters.cpu_percent = 80;
                break;
            case 'MemoryStress':
                parameters.memory_mb = 1024;
                break;
        }
        return parameters;
    }

    buildFaultType(faultType) {
        switch (faultType) {
            case 'Exception':
                return { Exception: 'Simulated exception for testing' };
            case 'Timeout':
                return { Timeout: 5000 };
            case 'ResourceExhaustion':
                return { ResourceExhaustion: 'Memory' };
            case 'NetworkFault':
                return { NetworkFault: { Latency: 1000 } };
            case 'AuthFailure':
                return 'AuthFailure';
            default:
                return { Exception: 'Unknown fault type' };
        }
    }

    monitorChaosTest(runId) {
        // Implementation would connect to WebSocket for real-time monitoring
        console.log('Monitoring chaos test:', runId);
    }

    monitorFaultInjection(runId) {
        // Implementation would connect to WebSocket for real-time monitoring
        console.log('Monitoring fault injection:', runId);
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
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
}

// Global functions for template usage
function startChaosTest() {
    analytics.startChaosTest();
}

function startFaultInjection() {
    analytics.startFaultInjection();
}

function analyzeTest(testName) {
    console.log('Analyzing test:', testName);
    // Implementation would show detailed test analysis
}

function quarantineTest(testName) {
    if (confirm(`Are you sure you want to quarantine the test: ${testName}?`)) {
        console.log('Quarantining test:', testName);
        // Implementation would quarantine the flaky test
    }
}

// Initialize analytics when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.analytics = new AdvancedTestAnalytics();
});
