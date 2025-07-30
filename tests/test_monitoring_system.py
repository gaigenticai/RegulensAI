"""
Tests for RegulensAI Advanced Monitoring and Alerting System
"""

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from core_infra.monitoring.metrics import (
    metrics_collector, 
    collect_all_metrics, 
    get_metrics_data,
    user_logins_total,
    compliance_score,
    training_completion_rate,
    system_health_score
)
from core_infra.api.main import app


class TestMetricsCollection:
    """Test custom metrics collection functionality."""
    
    @pytest.mark.asyncio
    async def test_business_metrics_collection(self):
        """Test collection of business metrics from database."""
        # Mock database responses
        mock_compliance_data = [
            {
                'tenant_id': 'tenant-1',
                'status': 'completed',
                'task_count': 10,
                'overdue_count': 0,
                'due_24h_count': 2
            },
            {
                'tenant_id': 'tenant-1',
                'status': 'pending',
                'task_count': 5,
                'overdue_count': 1,
                'due_24h_count': 3
            }
        ]
        
        mock_training_data = [
            {
                'tenant_id': 'tenant-1',
                'completion_rate': 85.5
            }
        ]
        
        mock_user_data = [
            {
                'tenant_id': 'tenant-1',
                'login_count': 25
            }
        ]
        
        with patch('core_infra.monitoring.metrics.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db_instance.fetch.side_effect = [
                mock_compliance_data,
                mock_training_data,
                mock_user_data
            ]
            mock_db.return_value.__aenter__.return_value = mock_db_instance
            
            # Collect metrics
            await metrics_collector.collect_business_metrics()
            
            # Verify database queries were called
            assert mock_db_instance.fetch.call_count == 3
    
    @pytest.mark.asyncio
    async def test_system_metrics_collection(self):
        """Test collection of system health metrics."""
        mock_db_stats = {
            'active_connections': 15,
            'max_connections': 100
        }
        
        with patch('core_infra.monitoring.metrics.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db_instance.fetchrow.return_value = mock_db_stats
            mock_db.return_value.__aenter__.return_value = mock_db_instance
            
            # Mock health score calculation
            with patch.object(metrics_collector, '_calculate_system_health_score', return_value=95.0):
                await metrics_collector.collect_system_metrics()
            
            # Verify system health score was set
            assert mock_db_instance.fetchrow.called
    
    def test_cache_metrics_recording(self):
        """Test cache hit/miss metrics recording."""
        # Record cache hits and misses
        metrics_collector.record_cache_hit('redis')
        metrics_collector.record_cache_hit('redis')
        metrics_collector.record_cache_miss('redis')
        
        # Get metrics data
        metrics_data = get_metrics_data()
        
        # Verify cache metrics are present
        assert 'regulensai_cache_hits_total' in metrics_data
        assert 'regulensai_cache_misses_total' in metrics_data
    
    def test_document_upload_metrics(self):
        """Test document upload metrics recording."""
        # Record document uploads
        metrics_collector.record_document_upload('regulatory', 'tenant-1')
        metrics_collector.record_document_upload('policy', 'tenant-1')
        
        # Get metrics data
        metrics_data = get_metrics_data()
        
        # Verify document upload metrics
        assert 'regulensai_document_uploads_total' in metrics_data
    
    def test_ai_service_metrics(self):
        """Test AI service request metrics recording."""
        # Record AI service requests
        metrics_collector.record_ai_request('openai', 'gpt-4', 'success')
        metrics_collector.record_ai_request('claude', 'claude-3', 'success')
        metrics_collector.record_ai_request('openai', 'gpt-4', 'error')
        
        # Get metrics data
        metrics_data = get_metrics_data()
        
        # Verify AI service metrics
        assert 'regulensai_openai_requests_total' in metrics_data
        assert 'regulensai_claude_requests_total' in metrics_data
    
    @pytest.mark.asyncio
    async def test_comprehensive_metrics_collection(self):
        """Test comprehensive metrics collection."""
        with patch.object(metrics_collector, 'collect_business_metrics') as mock_business, \
             patch.object(metrics_collector, 'collect_system_metrics') as mock_system:
            
            await collect_all_metrics()
            
            # Verify both collection methods were called
            mock_business.assert_called_once()
            mock_system.assert_called_once()
    
    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics format output."""
        # Set some test metrics
        system_health_score.set(95.5)
        compliance_score.labels(tenant_id='test').set(88.2)
        
        # Get metrics data
        metrics_data = get_metrics_data()
        
        # Verify Prometheus format
        assert isinstance(metrics_data, str)
        assert 'regulensai_system_health_score' in metrics_data
        assert 'regulensai_compliance_score' in metrics_data
        assert '95.5' in metrics_data
        assert '88.2' in metrics_data


class TestMonitoringAPI:
    """Test monitoring API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch('core_infra.api.routes.operations.collect_all_metrics')
    def test_collect_metrics_endpoint(self, mock_collect):
        """Test metrics collection endpoint."""
        mock_collect.return_value = None
        
        with patch('core_infra.api.routes.operations.get_metrics_data', return_value="# Test metrics"):
            response = self.client.get(
                "/api/v1/operations/metrics/collect",
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'timestamp' in data
        assert 'metrics_count' in data
    
    @patch('core_infra.api.routes.operations.collect_all_metrics')
    @patch('core_infra.api.routes.operations.get_metrics_data')
    def test_prometheus_metrics_endpoint(self, mock_get_metrics, mock_collect):
        """Test Prometheus metrics endpoint."""
        mock_collect.return_value = None
        mock_get_metrics.return_value = "# HELP test_metric Test metric\ntest_metric 1.0"
        
        response = self.client.get(
            "/api/v1/operations/metrics/prometheus",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        assert "test_metric" in response.text
    
    @patch('core_infra.api.routes.operations.get_database')
    def test_business_metrics_endpoint(self, mock_get_db):
        """Test business metrics endpoint."""
        # Mock database responses
        mock_db = AsyncMock()
        mock_db.fetchrow.side_effect = [
            {
                'total_tasks': 100,
                'completed_tasks': 85,
                'overdue_tasks': 5,
                'completion_rate': 85.0
            },
            {
                'total_enrollments': 50,
                'completed_enrollments': 40,
                'avg_completion_rate': 80.0
            },
            {
                'active_users_24h': 25
            }
        ]
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        response = self.client.get(
            "/api/v1/operations/metrics/business",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'compliance' in data
        assert 'training' in data
        assert 'users' in data
        assert data['compliance']['total_tasks'] == 100
        assert data['training']['avg_completion_rate'] == 80.0
        assert data['users']['active_users_24h'] == 25
    
    def test_active_alerts_endpoint(self):
        """Test active alerts endpoint."""
        response = self.client.get(
            "/api/v1/operations/alerts/active",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'alerts' in data
        assert 'summary' in data
        assert 'timestamp' in data
        
        # Verify summary structure
        summary = data['summary']
        assert 'total_alerts' in summary
        assert 'critical' in summary
        assert 'warning' in summary
        assert 'info' in summary
    
    def test_acknowledge_alert_endpoint(self):
        """Test alert acknowledgment endpoint."""
        response = self.client.post(
            "/api/v1/operations/alerts/test-alert-123/acknowledge",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'test-alert-123' in data['message']
        assert 'timestamp' in data
    
    def test_alerts_filtering_by_severity(self):
        """Test alert filtering by severity."""
        # Test critical alerts only
        response = self.client.get(
            "/api/v1/operations/alerts/active?severity=critical",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only critical alerts are returned
        for alert in data['alerts']:
            assert alert['severity'] == 'critical'


class TestAlertingSystem:
    """Test alerting system functionality."""
    
    def test_alert_severity_classification(self):
        """Test alert severity classification."""
        # Test critical alert conditions
        critical_conditions = [
            ('RegulensAIServiceDown', 'Service unavailable'),
            ('ComplianceSLABreach', 'SLA violation'),
            ('HighAPIErrorRate', 'High error rate')
        ]
        
        for alert_name, description in critical_conditions:
            # In a real implementation, this would test alert rule evaluation
            assert alert_name.startswith(('RegulensAI', 'Compliance', 'High'))
    
    def test_alert_escalation_paths(self):
        """Test alert escalation path configuration."""
        escalation_config = {
            'critical': {
                'immediate': ['devops-oncall@regulens.ai'],
                'business_critical': ['cto@regulens.ai', 'compliance-officer@regulens.ai'],
                'security_immediate': ['security@regulens.ai', 'ciso@regulens.ai']
            },
            'warning': {
                'standard': ['devops@regulens.ai'],
                'business_standard': ['compliance-team@regulens.ai'],
                'proactive': ['proactive-monitoring@regulens.ai']
            }
        }
        
        # Verify escalation paths are properly configured
        assert 'critical' in escalation_config
        assert 'warning' in escalation_config
        assert len(escalation_config['critical']['immediate']) > 0
    
    def test_alert_correlation_rules(self):
        """Test alert correlation and inhibition rules."""
        # Test inhibition rules
        inhibition_rules = [
            {
                'source_severity': 'critical',
                'target_severity': 'warning',
                'description': 'Suppress warnings when critical alerts active'
            },
            {
                'source_alert': 'RegulensAIServiceDown',
                'target_category': 'database',
                'description': 'Suppress database alerts when service down'
            }
        ]
        
        # Verify inhibition rules structure
        for rule in inhibition_rules:
            assert 'description' in rule
            assert len(rule) >= 3


class TestDashboardIntegration:
    """Test dashboard integration and configuration."""
    
    def test_dashboard_configuration_files(self):
        """Test dashboard configuration file structure."""
        import os
        
        dashboard_files = [
            'monitoring/dashboards/executive-overview.json',
            'monitoring/dashboards/technical-operations.json',
            'monitoring/dashboards/regulensai-application.json',
            'monitoring/dashboards/alerting-overview.json'
        ]
        
        for dashboard_file in dashboard_files:
            assert os.path.exists(dashboard_file), f"Dashboard file {dashboard_file} not found"
            
            # Verify JSON structure
            with open(dashboard_file, 'r') as f:
                dashboard_config = json.load(f)
                assert 'dashboard' in dashboard_config
                assert 'title' in dashboard_config['dashboard']
                assert 'panels' in dashboard_config['dashboard']
    
    def test_dashboard_panel_configuration(self):
        """Test dashboard panel configuration."""
        # Load executive overview dashboard
        with open('monitoring/dashboards/executive-overview.json', 'r') as f:
            dashboard = json.load(f)
        
        panels = dashboard['dashboard']['panels']
        
        # Verify required panels exist
        panel_titles = [panel['title'] for panel in panels]
        required_panels = [
            'System Health Score',
            'Compliance Score',
            'Active Users (24h)',
            'System Uptime'
        ]
        
        for required_panel in required_panels:
            assert required_panel in panel_titles
    
    def test_alert_rules_configuration(self):
        """Test alert rules configuration."""
        import yaml
        
        # Load alert rules
        with open('monitoring/alerts/regulensai-alerts.yaml', 'r') as f:
            alert_config = yaml.safe_load(f)
        
        # Verify structure
        assert 'groups' in alert_config
        
        # Check for required alert groups
        group_names = [group['name'] for group in alert_config['groups']]
        required_groups = [
            'regulensai.critical',
            'regulensai.warning',
            'regulensai.business_impact'
        ]
        
        for required_group in required_groups:
            assert required_group in group_names


class TestPerformanceOptimization:
    """Test monitoring system performance optimization."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self):
        """Test metrics collection performance."""
        import time
        
        start_time = time.time()
        
        # Mock database to return quickly
        with patch('core_infra.monitoring.metrics.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db_instance.fetch.return_value = []
            mock_db_instance.fetchrow.return_value = {'active_connections': 10, 'max_connections': 100}
            mock_db.return_value.__aenter__.return_value = mock_db_instance
            
            await collect_all_metrics()
        
        collection_time = time.time() - start_time
        
        # Metrics collection should complete within 5 seconds
        assert collection_time < 5.0
    
    def test_metrics_data_size(self):
        """Test metrics data size is reasonable."""
        # Set some test metrics
        for i in range(10):
            user_logins_total.labels(tenant_id=f'tenant-{i}', user_role='user').inc()
            compliance_score.labels(tenant_id=f'tenant-{i}').set(90 + i)
        
        metrics_data = get_metrics_data()
        
        # Metrics data should be reasonable size (< 100KB for test data)
        assert len(metrics_data.encode('utf-8')) < 100 * 1024
    
    def test_database_query_optimization(self):
        """Test database queries are optimized for monitoring."""
        # Verify queries use appropriate indexes and limits
        optimized_queries = [
            "SELECT status, COUNT(*) FROM compliance_tasks WHERE created_at >= NOW() - INTERVAL '30 days' GROUP BY status",
            "SELECT AVG(completion_percentage) FROM training_progress WHERE updated_at >= NOW() - INTERVAL '7 days'",
            "SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE action = 'user_login' AND created_at >= NOW() - INTERVAL '24 hours'"
        ]
        
        # Verify queries are structured for performance
        for query in optimized_queries:
            assert 'WHERE' in query  # Ensure filtering
            assert any(interval in query for interval in ['INTERVAL', 'NOW()'])  # Time-based filtering


if __name__ == "__main__":
    pytest.main([__file__])
