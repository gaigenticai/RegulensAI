/**
 * Disaster Recovery API Service
 * API client for DR management, testing, and monitoring
 */

import { apiClient } from './client';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface DRStatus {
  overall_status: string;
  health_score: number;
  components: Record<string, DRComponentStatus>;
  recent_events: DREvent[];
  recent_tests: DRTestResult[];
  last_updated: string;
}

export interface DRComponentStatus {
  status: string;
  rto_minutes: number;
  rpo_minutes: number;
  priority: number;
  automated_recovery: boolean;
  last_test_time: string | null;
  last_backup_time: string | null;
  dependencies: string[];
}

export interface DRComponent {
  component: string;
  status: string;
  rto_minutes: number;
  rpo_minutes: number;
  priority: number;
  automated_recovery: boolean;
  last_test_time: string | null;
  last_backup_time: string | null;
  dependencies: string[];
}

export interface DREvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  severity: string;
  component: string;
  description: string;
  status: string;
  recovery_actions: string[];
}

export interface DRTestResult {
  test_id: string;
  test_type: string;
  component: string;
  start_time: string;
  end_time: string | null;
  status: string;
  duration_minutes: number | null;
  rto_achieved: boolean | null;
  rpo_achieved: boolean | null;
  validation_results: Record<string, boolean>;
  error_messages: string[];
  recommendations: string[];
  metadata: Record<string, any>;
}

export interface DRTestRequest {
  component: string;
  test_type: string;
  dry_run?: boolean;
  notify_on_completion?: boolean;
}

export interface DRTestResponse {
  test_id: string;
  status: string;
  message: string;
  estimated_duration_minutes?: number;
}

export interface DRHealthScore {
  overall_score: number;
  component_scores: Record<string, {
    score: number;
    status: string;
    priority: number;
  }>;
  status: string;
  last_updated: string;
}

export interface DREventsParams {
  limit?: number;
  severity?: string;
  component?: string;
  hours?: number;
}

export interface DRTestResultsParams {
  limit?: number;
  component?: string;
  test_type?: string;
  status?: string;
}

export interface DRFullTestParams {
  dryRun?: boolean;
  notify_on_completion?: boolean;
}

// ============================================================================
// API SERVICE CLASS
// ============================================================================

class DisasterRecoveryAPI {
  private readonly basePath = '/api/v1/disaster-recovery';

  /**
   * Get comprehensive DR status
   */
  async getStatus(): Promise<DRStatus> {
    const response = await apiClient.get(`${this.basePath}/status`);
    return response.data;
  }

  /**
   * Get detailed status of all DR components
   */
  async getComponents(): Promise<DRComponent[]> {
    const response = await apiClient.get(`${this.basePath}/components`);
    return response.data;
  }

  /**
   * Get DR events with filtering options
   */
  async getEvents(params: DREventsParams = {}): Promise<{ events: DREvent[] }> {
    const response = await apiClient.get(`${this.basePath}/events`, { params });
    return { events: response.data };
  }

  /**
   * Get DR health score and breakdown
   */
  async getHealthScore(): Promise<DRHealthScore> {
    const response = await apiClient.get(`${this.basePath}/health-score`);
    return response.data;
  }

  /**
   * Run disaster recovery test for specific component
   */
  async runTest(request: DRTestRequest): Promise<DRTestResponse> {
    const response = await apiClient.post(`${this.basePath}/test`, request);
    return response.data;
  }

  /**
   * Run comprehensive disaster recovery test for all components
   */
  async runFullTest(params: DRFullTestParams = {}): Promise<DRTestResponse> {
    const response = await apiClient.post(`${this.basePath}/test/full`, null, { params });
    return response.data;
  }

  /**
   * Get DR test results with filtering options
   */
  async getTestResults(params: DRTestResultsParams = {}): Promise<{
    test_results: DRTestResult[];
    total_count: number;
    filters_applied: Record<string, any>;
  }> {
    const response = await apiClient.get(`${this.basePath}/test/results`, { params });
    return response.data;
  }

  /**
   * Get available test types
   */
  getTestTypes(): string[] {
    return [
      'backup_validation',
      'failover_test',
      'recovery_test',
      'full_dr_test',
      'network_partition',
      'database_failover',
      'application_failover'
    ];
  }

  /**
   * Get available component types
   */
  getComponentTypes(): string[] {
    return [
      'database',
      'api_services',
      'web_ui',
      'monitoring',
      'file_storage'
    ];
  }

  /**
   * Get severity levels
   */
  getSeverityLevels(): string[] {
    return [
      'info',
      'warning',
      'critical',
      'emergency'
    ];
  }

  /**
   * Get status types
   */
  getStatusTypes(): string[] {
    return [
      'healthy',
      'warning',
      'critical',
      'testing',
      'failover_in_progress',
      'recovery_in_progress',
      'failed'
    ];
  }

  /**
   * Format duration from minutes to human readable
   */
  formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }

  /**
   * Format relative time
   */
  formatRelativeTime(dateString: string | null): string {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes}m ago`;
    } else {
      return 'Just now';
    }
  }

  /**
   * Get status color for UI components
   */
  getStatusColor(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
      case 'failed':
        return 'error';
      case 'testing':
      case 'failover_in_progress':
      case 'recovery_in_progress':
        return 'info';
      default:
        return 'default';
    }
  }

  /**
   * Get severity color for UI components
   */
  getSeverityColor(severity: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (severity) {
      case 'info':
        return 'info';
      case 'warning':
        return 'warning';
      case 'critical':
      case 'emergency':
        return 'error';
      default:
        return 'default';
    }
  }

  /**
   * Get priority label
   */
  getPriorityLabel(priority: number): string {
    switch (priority) {
      case 1:
        return 'Critical';
      case 2:
        return 'High';
      case 3:
        return 'Medium';
      case 4:
        return 'Low';
      default:
        return 'Unknown';
    }
  }

  /**
   * Get priority color
   */
  getPriorityColor(priority: number): 'error' | 'warning' | 'info' | 'default' {
    switch (priority) {
      case 1:
        return 'error';
      case 2:
        return 'warning';
      case 3:
        return 'info';
      case 4:
      default:
        return 'default';
    }
  }

  /**
   * Calculate health score color
   */
  getHealthScoreColor(score: number): 'success' | 'warning' | 'error' {
    if (score >= 80) {
      return 'success';
    } else if (score >= 60) {
      return 'warning';
    } else {
      return 'error';
    }
  }

  /**
   * Validate test request
   */
  validateTestRequest(request: DRTestRequest): string[] {
    const errors: string[] = [];

    if (!request.component) {
      errors.push('Component is required');
    }

    if (!request.test_type) {
      errors.push('Test type is required');
    }

    const validTestTypes = this.getTestTypes();
    if (request.test_type && !validTestTypes.includes(request.test_type)) {
      errors.push(`Invalid test type. Must be one of: ${validTestTypes.join(', ')}`);
    }

    return errors;
  }

  /**
   * Estimate test duration
   */
  estimateTestDuration(component: string, testType: string): number {
    const baseDurations: Record<string, number> = {
      'backup_validation': 5,
      'failover_test': 15,
      'recovery_test': 30,
      'full_dr_test': 60
    };

    const componentMultipliers: Record<string, number> = {
      'database': 1.5,
      'api_services': 1.0,
      'web_ui': 0.5,
      'monitoring': 1.2,
      'file_storage': 2.0
    };

    const baseDuration = baseDurations[testType] || 10;
    const multiplier = componentMultipliers[component] || 1.0;

    return Math.round(baseDuration * multiplier);
  }
}

// ============================================================================
// EXPORT SINGLETON INSTANCE
// ============================================================================

export const drApi = new DisasterRecoveryAPI();
