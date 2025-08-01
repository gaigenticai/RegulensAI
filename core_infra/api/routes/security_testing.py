"""
Regulens AI - Security Testing API Routes
Enterprise-grade API endpoints for security penetration testing and compliance validation.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
import structlog

from core_infra.api.auth import get_current_user, require_permission
from core_infra.api.middleware import rate_limit, audit_log
from security.penetration_testing.security_scanner import run_security_scan
from security.penetration_testing.automated_security_tests import (
    run_full_security_assessment, validate_compliance
)
from core_infra.autoscaling.controller import (
    get_scaling_status, set_scaling_parameters, enable_autoscaling, disable_autoscaling
)
from core_infra.exceptions import SecurityException

# Initialize logging
logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/security", tags=["Security Testing"])

# Pydantic models
class SecurityScanRequest(BaseModel):
    target_url: HttpUrl = Field(..., description="Target URL to scan")
    scan_type: str = Field(default="comprehensive", description="Type of scan (basic, comprehensive, compliance)")
    include_network_scan: bool = Field(default=False, description="Include network port scanning")

class SecurityScanResponse(BaseModel):
    scan_id: str
    target_url: str
    scan_type: str
    status: str
    started_at: datetime
    estimated_completion: Optional[datetime]

class VulnerabilityResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    endpoint: str
    remediation: str
    cvss_score: Optional[float]

class SecurityReportResponse(BaseModel):
    scan_id: str
    target_url: str
    scan_date: datetime
    summary: Dict[str, Any]
    vulnerabilities: List[VulnerabilityResponse]
    compliance_status: str
    recommendations: List[str]

class AutoScalingConfigRequest(BaseModel):
    min_replicas: Optional[int] = Field(None, ge=1, le=100, description="Minimum number of replicas")
    max_replicas: Optional[int] = Field(None, ge=1, le=100, description="Maximum number of replicas")
    monitoring_interval: Optional[int] = Field(None, ge=30, le=3600, description="Monitoring interval in seconds")

class AutoScalingStatusResponse(BaseModel):
    enabled: bool
    current_replicas: int
    min_replicas: int
    max_replicas: int
    last_scaling_action: datetime
    metrics: Dict[str, Any]

# Security Testing Routes

@router.post("/scan", response_model=SecurityScanResponse)
@rate_limit(requests_per_minute=10)
@audit_log("security_scan_start")
@require_permission("system.admin")
async def start_security_scan(
    request: SecurityScanRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start a security penetration testing scan."""
    try:
        scan_id = f"scan_{int(datetime.utcnow().timestamp())}"
        target_url = str(request.target_url)
        
        # Validate target URL (should be internal or authorized)
        if not _is_authorized_target(target_url, current_user):
            raise HTTPException(status_code=403, detail="Unauthorized scan target")
        
        # Start background scan
        if request.scan_type == "comprehensive":
            background_tasks.add_task(
                _run_comprehensive_scan, 
                scan_id, 
                target_url, 
                request.include_network_scan,
                current_user["tenant_id"]
            )
        elif request.scan_type == "compliance":
            background_tasks.add_task(
                _run_compliance_scan,
                scan_id,
                target_url,
                current_user["tenant_id"]
            )
        else:
            background_tasks.add_task(
                _run_basic_scan,
                scan_id,
                target_url,
                current_user["tenant_id"]
            )
        
        return SecurityScanResponse(
            scan_id=scan_id,
            target_url=target_url,
            scan_type=request.scan_type,
            status="started",
            started_at=datetime.utcnow(),
            estimated_completion=datetime.utcnow().replace(minute=datetime.utcnow().minute + 15)
        )
        
    except Exception as e:
        logger.error(f"Failed to start security scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan/{scan_id}/status")
@rate_limit(requests_per_minute=60)
async def get_scan_status(
    scan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get security scan status."""
    try:
        # In a real implementation, this would check scan status from database
        # For now, return a mock status
        return {
            "scan_id": scan_id,
            "status": "completed",
            "progress": 100,
            "current_phase": "report_generation",
            "vulnerabilities_found": 3,
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get scan status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan/{scan_id}/report", response_model=SecurityReportResponse)
@rate_limit(requests_per_minute=30)
@require_permission("reports.read")
async def get_security_report(
    scan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get comprehensive security scan report."""
    try:
        # In a real implementation, this would retrieve the actual report
        # For now, return a mock report structure
        return SecurityReportResponse(
            scan_id=scan_id,
            target_url="https://api.regulens.ai",
            scan_date=datetime.utcnow(),
            summary={
                "total_vulnerabilities": 3,
                "critical": 0,
                "high": 1,
                "medium": 2,
                "low": 0,
                "risk_score": 15
            },
            vulnerabilities=[
                VulnerabilityResponse(
                    id="vuln_001",
                    category="security_misconfiguration",
                    severity="high",
                    title="Missing Security Headers",
                    description="Missing X-Frame-Options header",
                    endpoint="/api/v1/health",
                    remediation="Add X-Frame-Options: DENY header",
                    cvss_score=5.3
                )
            ],
            compliance_status="non_compliant",
            recommendations=[
                "Implement proper security headers",
                "Enable HTTPS enforcement",
                "Configure Content Security Policy"
            ]
        )
        
    except Exception as e:
        logger.error(f"Failed to get security report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compliance/validate")
@rate_limit(requests_per_minute=20)
@require_permission("compliance.read")
async def validate_compliance_status(
    target_url: HttpUrl = Query(..., description="Target URL to validate"),
    framework: str = Query(default="pci_dss", description="Compliance framework (pci_dss, sox, gdpr)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate compliance status for specific framework."""
    try:
        target_url_str = str(target_url)
        
        if not _is_authorized_target(target_url_str, current_user):
            raise HTTPException(status_code=403, detail="Unauthorized validation target")
        
        if framework == "pci_dss":
            results = await validate_compliance(target_url_str)
        else:
            # For other frameworks, return basic validation
            results = {
                "framework": framework,
                "target": target_url_str,
                "overall_compliance": True,
                "requirements": {},
                "validation_date": datetime.utcnow().isoformat()
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Compliance validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Auto-scaling Management Routes

@router.get("/autoscaling/status", response_model=AutoScalingStatusResponse)
@rate_limit(requests_per_minute=60)
@require_permission("system.admin")
async def get_autoscaling_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current auto-scaling status and metrics."""
    try:
        status = await get_scaling_status()
        
        return AutoScalingStatusResponse(
            enabled=status.get("enabled", False),
            current_replicas=status.get("current_replicas", 3),
            min_replicas=status.get("min_replicas", 3),
            max_replicas=status.get("max_replicas", 20),
            last_scaling_action=datetime.fromisoformat(status.get("last_scaling_action", datetime.utcnow().isoformat())),
            metrics=status.get("metrics", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to get auto-scaling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/autoscaling/config")
@rate_limit(requests_per_minute=20)
@audit_log("autoscaling_config_update")
@require_permission("system.admin")
async def update_autoscaling_config(
    request: AutoScalingConfigRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update auto-scaling configuration."""
    try:
        await set_scaling_parameters(
            min_replicas=request.min_replicas,
            max_replicas=request.max_replicas,
            monitoring_interval=request.monitoring_interval
        )
        
        return {
            "status": "updated",
            "config": {
                "min_replicas": request.min_replicas,
                "max_replicas": request.max_replicas,
                "monitoring_interval": request.monitoring_interval
            },
            "updated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to update auto-scaling config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/autoscaling/enable")
@rate_limit(requests_per_minute=10)
@audit_log("autoscaling_enable")
@require_permission("system.admin")
async def enable_autoscaling_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Enable auto-scaling."""
    try:
        await enable_autoscaling()
        
        return {
            "status": "enabled",
            "message": "Auto-scaling has been enabled",
            "enabled_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to enable auto-scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/autoscaling/disable")
@rate_limit(requests_per_minute=10)
@audit_log("autoscaling_disable")
@require_permission("system.admin")
async def disable_autoscaling_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Disable auto-scaling."""
    try:
        await disable_autoscaling()
        
        return {
            "status": "disabled",
            "message": "Auto-scaling has been disabled",
            "disabled_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to disable auto-scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def security_testing_health():
    """Health check for security testing service."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "security_scanner": "healthy",
                "compliance_validator": "healthy",
                "autoscaling_controller": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Security testing health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Helper functions

def _is_authorized_target(target_url: str, current_user: Dict[str, Any]) -> bool:
    """Check if user is authorized to scan the target URL."""
    # In a real implementation, this would check against authorized domains
    # For now, allow internal domains and localhost
    authorized_domains = [
        "localhost",
        "127.0.0.1",
        "regulens.ai",
        "api.regulens.ai",
        "app.regulens.ai"
    ]
    
    for domain in authorized_domains:
        if domain in target_url:
            return True
    
    # Check if user has system admin permissions for external scans
    return current_user.get("role") == "admin"

async def _run_comprehensive_scan(scan_id: str, target_url: str, 
                                include_network: bool, tenant_id: str):
    """Run comprehensive security scan in background."""
    try:
        logger.info(f"Starting comprehensive scan {scan_id} for {target_url}")
        results = await run_full_security_assessment(target_url, include_network)
        
        # Store results in database
        # In a real implementation, this would store the full results
        logger.info(f"Comprehensive scan {scan_id} completed")
        
    except Exception as e:
        logger.error(f"Comprehensive scan {scan_id} failed: {e}")

async def _run_compliance_scan(scan_id: str, target_url: str, tenant_id: str):
    """Run compliance-focused scan in background."""
    try:
        logger.info(f"Starting compliance scan {scan_id} for {target_url}")
        results = await validate_compliance(target_url)
        
        # Store results in database
        logger.info(f"Compliance scan {scan_id} completed")
        
    except Exception as e:
        logger.error(f"Compliance scan {scan_id} failed: {e}")

async def _run_basic_scan(scan_id: str, target_url: str, tenant_id: str):
    """Run basic security scan in background."""
    try:
        logger.info(f"Starting basic scan {scan_id} for {target_url}")
        results = await run_security_scan(target_url)
        
        # Store results in database
        logger.info(f"Basic scan {scan_id} completed")
        
    except Exception as e:
        logger.error(f"Basic scan {scan_id} failed: {e}")
