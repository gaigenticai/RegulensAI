"""
Regulens AI - Automated Security Testing Suite
Comprehensive automated security testing with OWASP compliance and reporting.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog

from security.penetration_testing.security_scanner import security_tester, run_security_scan
from core_infra.config import get_settings

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class OWASPZAPScanner:
    """OWASP ZAP integration for automated security scanning."""
    
    def __init__(self):
        self.zap_path = os.getenv("ZAP_PATH", "/opt/zaproxy/zap.sh")
        self.zap_port = 8080
        
    async def run_zap_scan(self, target_url: str) -> Dict[str, Any]:
        """Run OWASP ZAP automated scan."""
        try:
            # Start ZAP in daemon mode
            zap_cmd = [
                self.zap_path,
                "-daemon",
                "-port", str(self.zap_port),
                "-config", "api.disablekey=true"
            ]
            
            logger.info("Starting OWASP ZAP scanner")
            zap_process = subprocess.Popen(zap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for ZAP to start
            await asyncio.sleep(10)
            
            # Run spider scan
            spider_result = await self._run_spider_scan(target_url)
            
            # Run active scan
            active_result = await self._run_active_scan(target_url)
            
            # Get results
            alerts = await self._get_zap_alerts()
            
            # Stop ZAP
            zap_process.terminate()
            
            return {
                "spider_scan": spider_result,
                "active_scan": active_result,
                "alerts": alerts,
                "scan_completed": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ZAP scan failed: {e}")
            return {"error": str(e)}
    
    async def _run_spider_scan(self, target_url: str) -> Dict[str, Any]:
        """Run ZAP spider scan."""
        try:
            import requests
            
            # Start spider
            spider_url = f"http://localhost:{self.zap_port}/JSON/spider/action/scan/"
            response = requests.get(spider_url, params={"url": target_url})
            scan_id = response.json()["scan"]
            
            # Wait for spider to complete
            while True:
                status_url = f"http://localhost:{self.zap_port}/JSON/spider/view/status/"
                status_response = requests.get(status_url, params={"scanId": scan_id})
                status = int(status_response.json()["status"])
                
                if status >= 100:
                    break
                    
                await asyncio.sleep(2)
            
            # Get spider results
            results_url = f"http://localhost:{self.zap_port}/JSON/spider/view/results/"
            results_response = requests.get(results_url, params={"scanId": scan_id})
            
            return {
                "scan_id": scan_id,
                "status": "completed",
                "urls_found": len(results_response.json().get("results", []))
            }
            
        except Exception as e:
            logger.error(f"Spider scan failed: {e}")
            return {"error": str(e)}
    
    async def _run_active_scan(self, target_url: str) -> Dict[str, Any]:
        """Run ZAP active scan."""
        try:
            import requests
            
            # Start active scan
            scan_url = f"http://localhost:{self.zap_port}/JSON/ascan/action/scan/"
            response = requests.get(scan_url, params={"url": target_url})
            scan_id = response.json()["scan"]
            
            # Wait for scan to complete
            while True:
                status_url = f"http://localhost:{self.zap_port}/JSON/ascan/view/status/"
                status_response = requests.get(status_url, params={"scanId": scan_id})
                status = int(status_response.json()["status"])
                
                if status >= 100:
                    break
                    
                await asyncio.sleep(5)
            
            return {
                "scan_id": scan_id,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Active scan failed: {e}")
            return {"error": str(e)}
    
    async def _get_zap_alerts(self) -> List[Dict[str, Any]]:
        """Get ZAP scan alerts."""
        try:
            import requests
            
            alerts_url = f"http://localhost:{self.zap_port}/JSON/core/view/alerts/"
            response = requests.get(alerts_url)
            return response.json().get("alerts", [])
            
        except Exception as e:
            logger.error(f"Failed to get ZAP alerts: {e}")
            return []

class NmapScanner:
    """Nmap integration for network security scanning."""
    
    async def run_port_scan(self, target_host: str) -> Dict[str, Any]:
        """Run Nmap port scan."""
        try:
            # Extract host from URL
            if "://" in target_host:
                target_host = target_host.split("://")[1].split("/")[0]
            
            # Run Nmap scan
            nmap_cmd = [
                "nmap",
                "-sS",  # SYN scan
                "-O",   # OS detection
                "-sV",  # Service version detection
                "-A",   # Aggressive scan
                "--script=vuln",  # Vulnerability scripts
                "-oX", "-",  # XML output to stdout
                target_host
            ]
            
            logger.info(f"Running Nmap scan on {target_host}")
            result = subprocess.run(nmap_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {
                    "target": target_host,
                    "scan_output": result.stdout,
                    "status": "completed",
                    "scan_time": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "target": target_host,
                    "error": result.stderr,
                    "status": "failed"
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Nmap scan timed out")
            return {"error": "Scan timeout", "status": "timeout"}
        except Exception as e:
            logger.error(f"Nmap scan failed: {e}")
            return {"error": str(e), "status": "failed"}

class SSLTester:
    """SSL/TLS security testing."""
    
    async def test_ssl_configuration(self, target_url: str) -> Dict[str, Any]:
        """Test SSL/TLS configuration."""
        try:
            # Use testssl.sh if available
            testssl_cmd = [
                "testssl.sh",
                "--jsonfile", "-",
                "--quiet",
                target_url
            ]
            
            logger.info(f"Testing SSL configuration for {target_url}")
            result = subprocess.run(testssl_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                try:
                    ssl_results = json.loads(result.stdout)
                    return {
                        "target": target_url,
                        "ssl_results": ssl_results,
                        "status": "completed"
                    }
                except json.JSONDecodeError:
                    return {
                        "target": target_url,
                        "raw_output": result.stdout,
                        "status": "completed"
                    }
            else:
                # Fallback to basic SSL check
                return await self._basic_ssl_check(target_url)
                
        except subprocess.TimeoutExpired:
            logger.error("SSL test timed out")
            return {"error": "SSL test timeout", "status": "timeout"}
        except FileNotFoundError:
            # testssl.sh not available, use basic check
            return await self._basic_ssl_check(target_url)
        except Exception as e:
            logger.error(f"SSL test failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def _basic_ssl_check(self, target_url: str) -> Dict[str, Any]:
        """Basic SSL check using Python ssl module."""
        try:
            import ssl
            import socket
            from urllib.parse import urlparse
            
            parsed_url = urlparse(target_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    return {
                        "target": target_url,
                        "ssl_version": version,
                        "cipher_suite": cipher,
                        "certificate": {
                            "subject": dict(x[0] for x in cert.get("subject", [])),
                            "issuer": dict(x[0] for x in cert.get("issuer", [])),
                            "not_before": cert.get("notBefore"),
                            "not_after": cert.get("notAfter"),
                            "serial_number": cert.get("serialNumber")
                        },
                        "status": "completed"
                    }
                    
        except Exception as e:
            logger.error(f"Basic SSL check failed: {e}")
            return {"error": str(e), "status": "failed"}

class ComplianceValidator:
    """Financial compliance security validation."""
    
    async def validate_pci_dss_compliance(self, target_url: str) -> Dict[str, Any]:
        """Validate PCI DSS compliance requirements."""
        compliance_results = {
            "target": target_url,
            "pci_dss_version": "4.0",
            "requirements": {},
            "overall_compliance": True,
            "validation_date": datetime.utcnow().isoformat()
        }
        
        # Requirement 4: Encrypt transmission of cardholder data
        ssl_results = await SSLTester().test_ssl_configuration(target_url)
        compliance_results["requirements"]["req_4_encryption"] = {
            "description": "Encrypt transmission of cardholder data across open, public networks",
            "compliant": ssl_results.get("status") == "completed" and "error" not in ssl_results,
            "details": ssl_results
        }
        
        # Requirement 6: Develop and maintain secure systems
        security_scan = await run_security_scan(target_url)
        high_vulns = sum(1 for v in security_scan.get("vulnerabilities", []) 
                        if v.get("severity") in ["critical", "high"])
        compliance_results["requirements"]["req_6_secure_systems"] = {
            "description": "Develop and maintain secure systems and applications",
            "compliant": high_vulns == 0,
            "details": {
                "high_severity_vulnerabilities": high_vulns,
                "total_vulnerabilities": len(security_scan.get("vulnerabilities", []))
            }
        }
        
        # Update overall compliance
        compliance_results["overall_compliance"] = all(
            req["compliant"] for req in compliance_results["requirements"].values()
        )
        
        return compliance_results

class AutomatedSecurityTestSuite:
    """Main automated security testing coordinator."""
    
    def __init__(self):
        self.zap_scanner = OWASPZAPScanner()
        self.nmap_scanner = NmapScanner()
        self.ssl_tester = SSLTester()
        self.compliance_validator = ComplianceValidator()
        
    async def run_full_security_assessment(self, target_url: str, 
                                         include_network_scan: bool = False) -> Dict[str, Any]:
        """Run comprehensive security assessment."""
        try:
            logger.info(f"Starting full security assessment for {target_url}")
            start_time = datetime.utcnow()
            
            assessment_results = {
                "target_url": target_url,
                "assessment_id": f"assessment_{int(start_time.timestamp())}",
                "start_time": start_time.isoformat(),
                "tests": {}
            }
            
            # 1. Custom vulnerability scan
            logger.info("Running custom vulnerability scan")
            custom_scan = await run_security_scan(target_url)
            assessment_results["tests"]["custom_vulnerability_scan"] = custom_scan
            
            # 2. SSL/TLS testing
            logger.info("Testing SSL/TLS configuration")
            ssl_results = await self.ssl_tester.test_ssl_configuration(target_url)
            assessment_results["tests"]["ssl_tls_test"] = ssl_results
            
            # 3. OWASP ZAP scan (if available)
            try:
                logger.info("Running OWASP ZAP scan")
                zap_results = await self.zap_scanner.run_zap_scan(target_url)
                assessment_results["tests"]["owasp_zap_scan"] = zap_results
            except Exception as e:
                logger.warning(f"OWASP ZAP scan failed: {e}")
                assessment_results["tests"]["owasp_zap_scan"] = {"error": str(e)}
            
            # 4. Network scan (optional)
            if include_network_scan:
                logger.info("Running network port scan")
                nmap_results = await self.nmap_scanner.run_port_scan(target_url)
                assessment_results["tests"]["network_scan"] = nmap_results
            
            # 5. Compliance validation
            logger.info("Validating compliance requirements")
            compliance_results = await self.compliance_validator.validate_pci_dss_compliance(target_url)
            assessment_results["tests"]["compliance_validation"] = compliance_results
            
            # Generate summary
            end_time = datetime.utcnow()
            assessment_results["end_time"] = end_time.isoformat()
            assessment_results["duration_seconds"] = (end_time - start_time).total_seconds()
            assessment_results["summary"] = self._generate_assessment_summary(assessment_results)
            
            # Generate report
            report_path = await self._generate_security_report(assessment_results)
            assessment_results["report_path"] = report_path
            
            logger.info(f"Security assessment completed in {assessment_results['duration_seconds']:.2f} seconds")
            return assessment_results
            
        except Exception as e:
            logger.error(f"Security assessment failed: {e}")
            return {
                "target_url": target_url,
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _generate_assessment_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate assessment summary."""
        summary = {
            "total_tests": len(results["tests"]),
            "successful_tests": 0,
            "failed_tests": 0,
            "total_vulnerabilities": 0,
            "critical_vulnerabilities": 0,
            "high_vulnerabilities": 0,
            "compliance_status": "unknown"
        }
        
        for test_name, test_result in results["tests"].items():
            if "error" not in test_result:
                summary["successful_tests"] += 1
            else:
                summary["failed_tests"] += 1
            
            # Count vulnerabilities from custom scan
            if test_name == "custom_vulnerability_scan" and "vulnerabilities" in test_result:
                vulns = test_result["vulnerabilities"]
                summary["total_vulnerabilities"] += len(vulns)
                summary["critical_vulnerabilities"] += sum(1 for v in vulns if v.get("severity") == "critical")
                summary["high_vulnerabilities"] += sum(1 for v in vulns if v.get("severity") == "high")
            
            # Get compliance status
            if test_name == "compliance_validation" and "overall_compliance" in test_result:
                summary["compliance_status"] = "compliant" if test_result["overall_compliance"] else "non_compliant"
        
        return summary
    
    async def _generate_security_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive security report."""
        try:
            report_dir = "security_reports"
            os.makedirs(report_dir, exist_ok=True)
            
            report_filename = f"security_assessment_{results['assessment_id']}.json"
            report_path = os.path.join(report_dir, report_filename)
            
            with open(report_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Security report generated: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Failed to generate security report: {e}")
            return ""

# Global security test suite instance
security_test_suite = AutomatedSecurityTestSuite()

# Convenience functions
async def run_full_security_assessment(target_url: str, include_network_scan: bool = False) -> Dict[str, Any]:
    """Run comprehensive security assessment."""
    return await security_test_suite.run_full_security_assessment(target_url, include_network_scan)

async def validate_compliance(target_url: str) -> Dict[str, Any]:
    """Validate compliance requirements."""
    return await ComplianceValidator().validate_pci_dss_compliance(target_url)

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        include_network = len(sys.argv) > 2 and sys.argv[2].lower() == "true"
        
        async def main():
            results = await run_full_security_assessment(target, include_network)
            print(json.dumps(results, indent=2, default=str))
        
        asyncio.run(main())
    else:
        print("Usage: python automated_security_tests.py <target_url> [include_network_scan]")
        print("Example: python automated_security_tests.py https://api.regulens.ai true")
