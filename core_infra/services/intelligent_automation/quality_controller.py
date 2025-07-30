"""Quality Controller for Intelligent Automation

This module provides quality assurance and control mechanisms for
automated processes, ensuring accuracy, compliance, and reliability.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import statistics
import uuid

from core_infra.config import settings
from core_infra.exceptions import SystemException, ValidationError
from core_infra.monitoring.observability import monitor_performance

logger = logging.getLogger(__name__)


class QualityStatus(Enum):
    """Quality check status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


class CheckType(Enum):
    """Types of quality checks."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"


class QualityController:
    """
    Quality assurance and control service for automated processes.
    
    Features:
    - Automated quality checks
    - Accuracy validation
    - Compliance verification
    - Performance monitoring
    - Quality reporting
    """
    
    def __init__(self):
        """Initialize quality controller."""
        self.quality_checks = self._load_quality_checks()
        self.quality_history = []
        self.thresholds = {
            'minimum_score': 0.8,
            'warning_score': 0.9,
            'accuracy_threshold': 0.95,
            'completeness_threshold': 0.9
        }
        logger.info("Quality controller initialized")
    
    def _load_quality_checks(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined quality checks."""
        return {
            'data_accuracy': {
                'name': 'Data Accuracy Check',
                'type': CheckType.ACCURACY,
                'weight': 2.0,
                'mandatory': True
            },
            'completeness': {
                'name': 'Data Completeness Check', 
                'type': CheckType.COMPLETENESS,
                'weight': 1.5,
                'mandatory': True
            },
            'compliance': {
                'name': 'Regulatory Compliance Check',
                'type': CheckType.COMPLIANCE,
                'weight': 3.0,
                'mandatory': True
            },
            'performance': {
                'name': 'Performance Check',
                'type': CheckType.PERFORMANCE,
                'weight': 1.0,
                'mandatory': False
            }
        }
    
    @monitor_performance
    async def validate_execution(
        self,
        process_id: str,
        execution_id: str,
        execution_data: Dict[str, Any],
        check_types: List[CheckType] = None
    ) -> Dict[str, Any]:
        """Validate a process execution."""
        try:
            logger.info(f"Starting quality validation for execution {execution_id}")
            
            # Determine checks to run
            checks_to_run = self.quality_checks
            if check_types:
                checks_to_run = {
                    k: v for k, v in self.quality_checks.items()
                    if v['type'] in check_types
                }
            
            # Run quality checks
            check_results = {}
            for check_id, check_def in checks_to_run.items():
                result = await self._run_quality_check(check_def, execution_data)
                check_results[check_id] = result
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(check_results, checks_to_run)
            overall_status = self._determine_overall_status(overall_score, check_results)
            
            # Create quality report
            report = {
                'report_id': f"QR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{execution_id[:8]}",
                'process_id': process_id,
                'execution_id': execution_id,
                'overall_status': overall_status.value,
                'overall_score': overall_score,
                'check_results': check_results,
                'created_at': datetime.utcnow().isoformat(),
                'recommendations': self._generate_recommendations(check_results)
            }
            
            # Store report
            self.quality_history.append(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            raise SystemException(f"Quality validation failed: {str(e)}")
    
    async def _run_quality_check(
        self,
        check_def: Dict[str, Any],
        execution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single quality check."""
        check_type = check_def['type']
        
        try:
            if check_type == CheckType.ACCURACY:
                return await self._check_accuracy(execution_data)
            elif check_type == CheckType.COMPLETENESS:
                return await self._check_completeness(execution_data)
            elif check_type == CheckType.COMPLIANCE:
                return await self._check_compliance(execution_data)
            elif check_type == CheckType.PERFORMANCE:
                return await self._check_performance(execution_data)
            else:
                return {
                    'status': QualityStatus.PENDING.value,
                    'score': 0,
                    'details': {'error': 'Unknown check type'}
                }
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {
                'status': QualityStatus.FAILED.value,
                'score': 0,
                'details': {'error': str(e)}
            }
    
    async def _check_accuracy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data accuracy."""
        score = 0
        issues = []
        
        # Check field match rate
        if 'extracted_fields' in data and 'expected_fields' in data:
            extracted = set(data['extracted_fields'].keys())
            expected = set(data['expected_fields'])
            match_rate = len(extracted & expected) / len(expected) if expected else 0
            
            if match_rate >= self.thresholds['accuracy_threshold']:
                score = match_rate
            else:
                issues.append(f"Field match rate {match_rate:.2%} below threshold")
        else:
            # Default accuracy check
            score = 0.95 if data.get('validation_passed', True) else 0.5
        
        status = QualityStatus.PASSED if score >= self.thresholds['accuracy_threshold'] else QualityStatus.FAILED
        
        return {
            'status': status.value,
            'score': score,
            'details': {
                'match_rate': match_rate if 'match_rate' in locals() else None,
                'issues': issues
            }
        }
    
    async def _check_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data completeness."""
        extracted_fields = data.get('extracted_fields', {})
        required_fields = data.get('required_fields', [])
        
        if required_fields:
            missing_fields = [f for f in required_fields if f not in extracted_fields]
            completeness_rate = 1 - (len(missing_fields) / len(required_fields))
        else:
            # Check for empty values
            total_fields = len(extracted_fields)
            empty_fields = sum(1 for v in extracted_fields.values() if not v)
            completeness_rate = 1 - (empty_fields / total_fields) if total_fields > 0 else 1
        
        status = QualityStatus.PASSED if completeness_rate >= self.thresholds['completeness_threshold'] else QualityStatus.WARNING
        
        return {
            'status': status.value,
            'score': completeness_rate,
            'details': {
                'completeness_rate': completeness_rate,
                'missing_fields': missing_fields if 'missing_fields' in locals() else []
            }
        }
    
    async def _check_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check regulatory compliance."""
        compliance_issues = []
        score = 1.0
        
        # GDPR compliance
        if not data.get('personal_data_consent', True):
            compliance_issues.append("Missing personal data consent")
            score -= 0.3
        
        # Data encryption
        if not data.get('data_encrypted', True):
            compliance_issues.append("Data not encrypted")
            score -= 0.3
        
        # Audit trail
        if not data.get('audit_trail', {}).get('complete', True):
            compliance_issues.append("Incomplete audit trail")
            score -= 0.2
        
        status = QualityStatus.PASSED if not compliance_issues else QualityStatus.FAILED
        
        return {
            'status': status.value,
            'score': max(0, score),
            'details': {'compliance_issues': compliance_issues}
        }
    
    async def _check_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check performance metrics."""
        score = 1.0
        performance_issues = []
        
        # Check execution time
        execution_time = data.get('execution_time_ms', 0)
        if execution_time > 5000:  # 5 seconds
            score -= 0.3
            performance_issues.append(f"Slow execution: {execution_time}ms")
        
        # Check resource usage
        memory_usage = data.get('memory_usage_mb', 0)
        if memory_usage > 512:
            score -= 0.2
            performance_issues.append(f"High memory usage: {memory_usage}MB")
        
        status = QualityStatus.PASSED if score >= 0.8 else QualityStatus.WARNING
        
        return {
            'status': status.value,
            'score': score,
            'details': {
                'execution_time_ms': execution_time,
                'memory_usage_mb': memory_usage,
                'issues': performance_issues
            }
        }
    
    def _calculate_overall_score(
        self,
        results: Dict[str, Dict[str, Any]],
        checks: Dict[str, Dict[str, Any]]
    ) -> float:
        """Calculate weighted overall score."""
        total_weight = sum(check['weight'] for check in checks.values())
        weighted_score = sum(
            results[check_id]['score'] * checks[check_id]['weight']
            for check_id in results
        )
        
        return weighted_score / total_weight if total_weight > 0 else 0
    
    def _determine_overall_status(
        self,
        overall_score: float,
        results: Dict[str, Dict[str, Any]]
    ) -> QualityStatus:
        """Determine overall quality status."""
        # Check for any failed mandatory checks
        if any(r['status'] == QualityStatus.FAILED.value for r in results.values()):
            return QualityStatus.FAILED
        
        # Check overall score
        if overall_score >= self.thresholds['warning_score']:
            return QualityStatus.PASSED
        elif overall_score >= self.thresholds['minimum_score']:
            return QualityStatus.WARNING
        else:
            return QualityStatus.FAILED
    
    def _generate_recommendations(self, results: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []
        
        for check_id, result in results.items():
            if result['status'] != QualityStatus.PASSED.value:
                if check_id == 'data_accuracy':
                    recommendations.append("Improve field extraction accuracy")
                elif check_id == 'completeness':
                    recommendations.append("Ensure all required fields are captured")
                elif check_id == 'compliance':
                    recommendations.append("Address compliance issues immediately")
                elif check_id == 'performance':
                    recommendations.append("Optimize process performance")
        
        return recommendations
    
    async def get_quality_trends(self, process_id: str, days: int = 30) -> Dict[str, Any]:
        """Get quality trends for a process."""
        # Filter reports for the process
        recent_reports = [
            report for report in self.quality_history
            if report['process_id'] == process_id and
            datetime.fromisoformat(report['created_at']) > datetime.utcnow() - timedelta(days=days)
        ]
        
        if not recent_reports:
            return {'process_id': process_id, 'no_data': True}
        
        scores = [report['overall_score'] for report in recent_reports]
        
        return {
            'process_id': process_id,
            'period_days': days,
            'report_count': len(recent_reports),
            'average_score': statistics.mean(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'trend': 'improving' if scores[-1] > scores[0] else 'declining' if scores else 'stable',
            'pass_rate': sum(1 for r in recent_reports if r['overall_status'] == 'passed') / len(recent_reports)
        }
    
    async def generate_quality_report(
        self,
        process_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        # Filter reports by date range
        filtered_reports = []
        for report in self.quality_history:
            if report['process_id'] != process_id:
                continue
            
            report_date = datetime.fromisoformat(report['created_at'])
            if start_date and report_date < start_date:
                continue
            if end_date and report_date > end_date:
                continue
            
            filtered_reports.append(report)
        
        if not filtered_reports:
            return {'error': 'No data available for the specified criteria'}
        
        # Aggregate statistics
        total_checks = len(filtered_reports)
        passed_checks = sum(1 for r in filtered_reports if r['overall_status'] == 'passed')
        
        # Check-specific stats
        check_stats = {}
        for check_id in self.quality_checks:
            check_results = [
                r['check_results'].get(check_id, {})
                for r in filtered_reports
                if check_id in r.get('check_results', {})
            ]
            
            if check_results:
                scores = [r['score'] for r in check_results if 'score' in r]
                check_stats[check_id] = {
                    'average_score': statistics.mean(scores) if scores else 0,
                    'pass_rate': sum(1 for r in check_results if r.get('status') == 'passed') / len(check_results)
                }
        
        return {
            'process_id': process_id,
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'summary': {
                'total_executions': total_checks,
                'passed': passed_checks,
                'pass_rate': passed_checks / total_checks if total_checks > 0 else 0
            },
            'check_statistics': check_stats,
            'recommendations': self._get_improvement_areas(filtered_reports)
        }
    
    def _get_improvement_areas(self, reports: List[Dict[str, Any]]) -> List[str]:
        """Identify areas for improvement based on historical data."""
        areas = []
        
        # Count failures by check type
        failure_counts = {}
        for report in reports:
            for check_id, result in report.get('check_results', {}).items():
                if result.get('status') != 'passed':
                    failure_counts[check_id] = failure_counts.get(check_id, 0) + 1
        
        # Generate recommendations based on failure patterns
        for check_id, count in failure_counts.items():
            if count > len(reports) * 0.2:  # Failing more than 20% of the time
                check_name = self.quality_checks.get(check_id, {}).get('name', check_id)
                areas.append(f"Focus on improving {check_name} (failed {count}/{len(reports)} times)")
        
        return areas[:5]  # Return top 5 areas


# Global quality controller instance
quality_controller = QualityController()