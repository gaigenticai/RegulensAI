"""
Regulens AI - Security Penetration Testing Framework
Automated security testing with OWASP Top 10 vulnerability scanning and compliance validation.
"""

import asyncio
import json
import uuid
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import SystemException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class VulnerabilityLevel(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class TestCategory(Enum):
    """Security test categories."""
    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XXE = "xml_external_entities"
    BROKEN_ACCESS = "broken_access_control"
    SECURITY_MISCONFIG = "security_misconfiguration"
    XSS = "cross_site_scripting"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    VULNERABLE_COMPONENTS = "vulnerable_components"
    INSUFFICIENT_LOGGING = "insufficient_logging"

@dataclass
class SecurityVulnerability:
    """Security vulnerability data structure."""
    id: str
    category: TestCategory
    severity: VulnerabilityLevel
    title: str
    description: str
    endpoint: str
    method: str
    payload: Optional[str]
    evidence: Dict[str, Any]
    remediation: str
    cwe_id: Optional[str]
    cvss_score: Optional[float]
    discovered_at: datetime

@dataclass
class SecurityTestResult:
    """Security test result data structure."""
    test_id: str
    test_name: str
    category: TestCategory
    target_url: str
    status: str
    vulnerabilities: List[SecurityVulnerability]
    execution_time_ms: int
    executed_at: datetime

class SQLInjectionTester:
    """SQL injection vulnerability testing."""
    
    def __init__(self):
        self.payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "'; DROP TABLE users; --",
            "' UNION SELECT NULL, NULL, NULL --",
            "1' AND (SELECT COUNT(*) FROM information_schema.tables) > 0 --",
            "1' AND (SELECT SUBSTRING(@@version,1,1)) = '5' --"
        ]
        
    async def test_endpoint(self, session: aiohttp.ClientSession, url: str, 
                          params: Dict[str, str], headers: Dict[str, str]) -> List[SecurityVulnerability]:
        """Test endpoint for SQL injection vulnerabilities."""
        vulnerabilities = []
        
        for param_name, param_value in params.items():
            for payload in self.payloads:
                try:
                    # Test with malicious payload
                    test_params = params.copy()
                    test_params[param_name] = payload
                    
                    async with session.get(url, params=test_params, headers=headers) as response:
                        response_text = await response.text()
                        
                        # Check for SQL error indicators
                        sql_errors = [
                            "sql syntax",
                            "mysql_fetch",
                            "ora-01756",
                            "microsoft ole db",
                            "postgresql",
                            "sqlite_master",
                            "syntax error"
                        ]
                        
                        for error in sql_errors:
                            if error.lower() in response_text.lower():
                                vulnerability = SecurityVulnerability(
                                    id=str(uuid.uuid4()),
                                    category=TestCategory.INJECTION,
                                    severity=VulnerabilityLevel.HIGH,
                                    title="SQL Injection Vulnerability",
                                    description=f"SQL injection detected in parameter '{param_name}'",
                                    endpoint=url,
                                    method="GET",
                                    payload=payload,
                                    evidence={
                                        "parameter": param_name,
                                        "error_pattern": error,
                                        "response_status": response.status,
                                        "response_snippet": response_text[:500]
                                    },
                                    remediation="Use parameterized queries and input validation",
                                    cwe_id="CWE-89",
                                    cvss_score=8.1,
                                    discovered_at=datetime.utcnow()
                                )
                                vulnerabilities.append(vulnerability)
                                break
                                
                except Exception as e:
                    logger.debug(f"SQL injection test error: {e}")
                    
        return vulnerabilities

class XSSTester:
    """Cross-site scripting vulnerability testing."""
    
    def __init__(self):
        self.payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
    async def test_endpoint(self, session: aiohttp.ClientSession, url: str,
                          params: Dict[str, str], headers: Dict[str, str]) -> List[SecurityVulnerability]:
        """Test endpoint for XSS vulnerabilities."""
        vulnerabilities = []
        
        for param_name, param_value in params.items():
            for payload in self.payloads:
                try:
                    # Test with XSS payload
                    test_params = params.copy()
                    test_params[param_name] = payload
                    
                    async with session.get(url, params=test_params, headers=headers) as response:
                        response_text = await response.text()
                        
                        # Check if payload is reflected without encoding
                        if payload in response_text:
                            vulnerability = SecurityVulnerability(
                                id=str(uuid.uuid4()),
                                category=TestCategory.XSS,
                                severity=VulnerabilityLevel.MEDIUM,
                                title="Cross-Site Scripting (XSS) Vulnerability",
                                description=f"XSS vulnerability detected in parameter '{param_name}'",
                                endpoint=url,
                                method="GET",
                                payload=payload,
                                evidence={
                                    "parameter": param_name,
                                    "reflected_payload": payload,
                                    "response_status": response.status,
                                    "content_type": response.headers.get("content-type", "")
                                },
                                remediation="Implement proper input validation and output encoding",
                                cwe_id="CWE-79",
                                cvss_score=6.1,
                                discovered_at=datetime.utcnow()
                            )
                            vulnerabilities.append(vulnerability)
                            break
                            
                except Exception as e:
                    logger.debug(f"XSS test error: {e}")
                    
        return vulnerabilities

class AuthenticationTester:
    """Authentication and authorization vulnerability testing."""
    
    async def test_broken_authentication(self, session: aiohttp.ClientSession, 
                                       base_url: str) -> List[SecurityVulnerability]:
        """Test for broken authentication vulnerabilities."""
        vulnerabilities = []
        
        # Test weak password policies
        weak_passwords = ["password", "123456", "admin", "test", ""]
        
        for password in weak_passwords:
            try:
                login_data = {
                    "email": "admin@test.com",
                    "password": password
                }
                
                async with session.post(f"{base_url}/api/v1/auth/login", 
                                      json=login_data) as response:
                    if response.status == 200:
                        vulnerability = SecurityVulnerability(
                            id=str(uuid.uuid4()),
                            category=TestCategory.BROKEN_AUTH,
                            severity=VulnerabilityLevel.HIGH,
                            title="Weak Password Policy",
                            description=f"Weak password '{password}' accepted",
                            endpoint=f"{base_url}/api/v1/auth/login",
                            method="POST",
                            payload=json.dumps(login_data),
                            evidence={
                                "weak_password": password,
                                "response_status": response.status
                            },
                            remediation="Implement strong password policies and account lockout",
                            cwe_id="CWE-521",
                            cvss_score=7.5,
                            discovered_at=datetime.utcnow()
                        )
                        vulnerabilities.append(vulnerability)
                        
            except Exception as e:
                logger.debug(f"Authentication test error: {e}")
        
        # Test for session fixation
        await self._test_session_fixation(session, base_url, vulnerabilities)
        
        return vulnerabilities
    
    async def _test_session_fixation(self, session: aiohttp.ClientSession, 
                                   base_url: str, vulnerabilities: List[SecurityVulnerability]):
        """Test for session fixation vulnerabilities."""
        try:
            # Get initial session
            async with session.get(f"{base_url}/api/v1/health") as response:
                initial_cookies = response.cookies
            
            # Attempt login
            login_data = {"email": "test@test.com", "password": "testpass"}
            async with session.post(f"{base_url}/api/v1/auth/login", 
                                  json=login_data) as response:
                if response.status == 200:
                    post_login_cookies = response.cookies
                    
                    # Check if session ID changed
                    if initial_cookies == post_login_cookies:
                        vulnerability = SecurityVulnerability(
                            id=str(uuid.uuid4()),
                            category=TestCategory.BROKEN_AUTH,
                            severity=VulnerabilityLevel.MEDIUM,
                            title="Session Fixation Vulnerability",
                            description="Session ID does not change after authentication",
                            endpoint=f"{base_url}/api/v1/auth/login",
                            method="POST",
                            payload=None,
                            evidence={
                                "session_unchanged": True,
                                "initial_cookies": str(initial_cookies),
                                "post_login_cookies": str(post_login_cookies)
                            },
                            remediation="Regenerate session ID after successful authentication",
                            cwe_id="CWE-384",
                            cvss_score=5.3,
                            discovered_at=datetime.utcnow()
                        )
                        vulnerabilities.append(vulnerability)
                        
        except Exception as e:
            logger.debug(f"Session fixation test error: {e}")

class SecurityHeadersTester:
    """Security headers vulnerability testing."""
    
    def __init__(self):
        self.required_headers = {
            "X-Frame-Options": "Security header to prevent clickjacking",
            "X-Content-Type-Options": "Prevents MIME type sniffing",
            "X-XSS-Protection": "XSS protection header",
            "Strict-Transport-Security": "HTTPS enforcement header",
            "Content-Security-Policy": "Content security policy header"
        }
        
    async def test_security_headers(self, session: aiohttp.ClientSession, 
                                  url: str) -> List[SecurityVulnerability]:
        """Test for missing security headers."""
        vulnerabilities = []
        
        try:
            async with session.get(url) as response:
                response_headers = response.headers
                
                for header_name, description in self.required_headers.items():
                    if header_name not in response_headers:
                        vulnerability = SecurityVulnerability(
                            id=str(uuid.uuid4()),
                            category=TestCategory.SECURITY_MISCONFIG,
                            severity=VulnerabilityLevel.MEDIUM,
                            title=f"Missing Security Header: {header_name}",
                            description=f"Missing {header_name} header: {description}",
                            endpoint=url,
                            method="GET",
                            payload=None,
                            evidence={
                                "missing_header": header_name,
                                "all_headers": dict(response_headers)
                            },
                            remediation=f"Add {header_name} header to all responses",
                            cwe_id="CWE-16",
                            cvss_score=4.3,
                            discovered_at=datetime.utcnow()
                        )
                        vulnerabilities.append(vulnerability)
                        
        except Exception as e:
            logger.debug(f"Security headers test error: {e}")
            
        return vulnerabilities

class ComplianceTester:
    """Financial compliance security testing."""
    
    async def test_pci_compliance(self, session: aiohttp.ClientSession, 
                                base_url: str) -> List[SecurityVulnerability]:
        """Test PCI DSS compliance requirements."""
        vulnerabilities = []
        
        # Test for unencrypted data transmission
        try:
            # Test if HTTP is accepted (should redirect to HTTPS)
            http_url = base_url.replace("https://", "http://")
            async with session.get(http_url, allow_redirects=False) as response:
                if response.status != 301 and response.status != 302:
                    vulnerability = SecurityVulnerability(
                        id=str(uuid.uuid4()),
                        category=TestCategory.SENSITIVE_DATA,
                        severity=VulnerabilityLevel.HIGH,
                        title="Unencrypted Data Transmission",
                        description="HTTP connections accepted without HTTPS redirect",
                        endpoint=http_url,
                        method="GET",
                        payload=None,
                        evidence={
                            "http_status": response.status,
                            "location_header": response.headers.get("Location", "")
                        },
                        remediation="Enforce HTTPS for all connections",
                        cwe_id="CWE-319",
                        cvss_score=7.4,
                        discovered_at=datetime.utcnow()
                    )
                    vulnerabilities.append(vulnerability)
                    
        except Exception as e:
            logger.debug(f"PCI compliance test error: {e}")
            
        return vulnerabilities

class SecurityPenetrationTester:
    """Main security penetration testing coordinator."""
    
    def __init__(self):
        self.sql_tester = SQLInjectionTester()
        self.xss_tester = XSSTester()
        self.auth_tester = AuthenticationTester()
        self.headers_tester = SecurityHeadersTester()
        self.compliance_tester = ComplianceTester()
        
    async def run_comprehensive_scan(self, target_url: str, 
                                   auth_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Run comprehensive security scan."""
        try:
            start_time = datetime.utcnow()
            all_vulnerabilities = []
            test_results = []
            
            # Setup HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                
                # Test 1: SQL Injection
                sql_vulns = await self._test_sql_injection(session, target_url, auth_headers)
                all_vulnerabilities.extend(sql_vulns)
                test_results.append(SecurityTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name="SQL Injection Test",
                    category=TestCategory.INJECTION,
                    target_url=target_url,
                    status="completed",
                    vulnerabilities=sql_vulns,
                    execution_time_ms=0,
                    executed_at=datetime.utcnow()
                ))
                
                # Test 2: XSS
                xss_vulns = await self._test_xss(session, target_url, auth_headers)
                all_vulnerabilities.extend(xss_vulns)
                test_results.append(SecurityTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name="Cross-Site Scripting Test",
                    category=TestCategory.XSS,
                    target_url=target_url,
                    status="completed",
                    vulnerabilities=xss_vulns,
                    execution_time_ms=0,
                    executed_at=datetime.utcnow()
                ))
                
                # Test 3: Authentication
                auth_vulns = await self.auth_tester.test_broken_authentication(session, target_url)
                all_vulnerabilities.extend(auth_vulns)
                test_results.append(SecurityTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name="Authentication Security Test",
                    category=TestCategory.BROKEN_AUTH,
                    target_url=target_url,
                    status="completed",
                    vulnerabilities=auth_vulns,
                    execution_time_ms=0,
                    executed_at=datetime.utcnow()
                ))
                
                # Test 4: Security Headers
                header_vulns = await self.headers_tester.test_security_headers(session, target_url)
                all_vulnerabilities.extend(header_vulns)
                test_results.append(SecurityTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name="Security Headers Test",
                    category=TestCategory.SECURITY_MISCONFIG,
                    target_url=target_url,
                    status="completed",
                    vulnerabilities=header_vulns,
                    execution_time_ms=0,
                    executed_at=datetime.utcnow()
                ))
                
                # Test 5: Compliance
                compliance_vulns = await self.compliance_tester.test_pci_compliance(session, target_url)
                all_vulnerabilities.extend(compliance_vulns)
                test_results.append(SecurityTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name="PCI Compliance Test",
                    category=TestCategory.SENSITIVE_DATA,
                    target_url=target_url,
                    status="completed",
                    vulnerabilities=compliance_vulns,
                    execution_time_ms=0,
                    executed_at=datetime.utcnow()
                ))
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Generate report
            report = await self._generate_security_report(
                target_url, all_vulnerabilities, test_results, execution_time
            )
            
            # Store results
            await self._store_scan_results(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            raise SystemException(f"Security scan failed: {e}")
    
    async def _test_sql_injection(self, session: aiohttp.ClientSession, 
                                target_url: str, auth_headers: Optional[Dict[str, str]]) -> List[SecurityVulnerability]:
        """Test SQL injection on common endpoints."""
        vulnerabilities = []
        headers = auth_headers or {}
        
        # Test common endpoints
        test_endpoints = [
            f"{target_url}/api/v1/customers",
            f"{target_url}/api/v1/transactions",
            f"{target_url}/api/v1/compliance/programs"
        ]
        
        for endpoint in test_endpoints:
            test_params = {"search": "test", "filter": "active", "page": "1"}
            vulns = await self.sql_tester.test_endpoint(session, endpoint, test_params, headers)
            vulnerabilities.extend(vulns)
            
        return vulnerabilities
    
    async def _test_xss(self, session: aiohttp.ClientSession, 
                      target_url: str, auth_headers: Optional[Dict[str, str]]) -> List[SecurityVulnerability]:
        """Test XSS on common endpoints."""
        vulnerabilities = []
        headers = auth_headers or {}
        
        # Test endpoints that might reflect user input
        test_endpoints = [
            f"{target_url}/api/v1/ui/documentation/search",
        ]
        
        for endpoint in test_endpoints:
            test_params = {"query": "test", "type": "api"}
            vulns = await self.xss_tester.test_endpoint(session, endpoint, test_params, headers)
            vulnerabilities.extend(vulns)
            
        return vulnerabilities
    
    async def _generate_security_report(self, target_url: str, vulnerabilities: List[SecurityVulnerability],
                                      test_results: List[SecurityTestResult], execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        # Categorize vulnerabilities by severity
        severity_counts = {level.value: 0 for level in VulnerabilityLevel}
        for vuln in vulnerabilities:
            severity_counts[vuln.severity.value] += 1
        
        # Calculate risk score
        risk_score = (
            severity_counts['critical'] * 10 +
            severity_counts['high'] * 7 +
            severity_counts['medium'] * 4 +
            severity_counts['low'] * 1
        )
        
        return {
            "scan_id": str(uuid.uuid4()),
            "target_url": target_url,
            "scan_date": datetime.utcnow().isoformat(),
            "execution_time_ms": execution_time,
            "summary": {
                "total_vulnerabilities": len(vulnerabilities),
                "severity_breakdown": severity_counts,
                "risk_score": risk_score,
                "compliance_status": "non_compliant" if vulnerabilities else "compliant"
            },
            "vulnerabilities": [asdict(vuln) for vuln in vulnerabilities],
            "test_results": [asdict(result) for result in test_results],
            "recommendations": self._generate_recommendations(vulnerabilities)
        }
    
    def _generate_recommendations(self, vulnerabilities: List[SecurityVulnerability]) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        
        if any(v.category == TestCategory.INJECTION for v in vulnerabilities):
            recommendations.append("Implement parameterized queries and input validation")
        
        if any(v.category == TestCategory.XSS for v in vulnerabilities):
            recommendations.append("Implement proper output encoding and Content Security Policy")
        
        if any(v.category == TestCategory.BROKEN_AUTH for v in vulnerabilities):
            recommendations.append("Strengthen authentication mechanisms and session management")
        
        if any(v.category == TestCategory.SECURITY_MISCONFIG for v in vulnerabilities):
            recommendations.append("Configure proper security headers and server hardening")
        
        if any(v.category == TestCategory.SENSITIVE_DATA for v in vulnerabilities):
            recommendations.append("Enforce HTTPS and implement proper data encryption")
        
        return recommendations
    
    async def _store_scan_results(self, report: Dict[str, Any]):
        """Store scan results in database."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO security_scan_results (
                        id, target_url, scan_date, execution_time_ms, 
                        total_vulnerabilities, risk_score, report_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    uuid.UUID(report["scan_id"]),
                    report["target_url"],
                    datetime.fromisoformat(report["scan_date"].replace('Z', '+00:00')),
                    report["execution_time_ms"],
                    report["summary"]["total_vulnerabilities"],
                    report["summary"]["risk_score"],
                    report
                )
        except Exception as e:
            logger.error(f"Failed to store scan results: {e}")

# Global security tester instance
security_tester = SecurityPenetrationTester()

# Convenience functions
async def run_security_scan(target_url: str, auth_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Run comprehensive security scan."""
    return await security_tester.run_comprehensive_scan(target_url, auth_headers)
