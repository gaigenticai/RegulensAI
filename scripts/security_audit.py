#!/usr/bin/env python3
"""
Regulens AI - Security Audit Script
Comprehensive security audit to detect hardcoded secrets, vulnerabilities, and security issues.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import structlog

# Initialize logging
logger = structlog.get_logger(__name__)

@dataclass
class SecurityFinding:
    """Security finding data structure."""
    severity: str  # critical, high, medium, low
    category: str  # secrets, passwords, vulnerabilities, etc.
    file_path: str
    line_number: int
    description: str
    evidence: str
    recommendation: str

class SecurityAuditor:
    """Comprehensive security auditor for the codebase."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []
        
        # Patterns for detecting security issues
        self.secret_patterns = {
            'api_key': [
                r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']',
                r'apikey["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']',
                r'["\']sk-[a-zA-Z0-9]{20,}["\']',  # OpenAI API keys
                r'["\']pk_[a-zA-Z0-9]{20,}["\']',  # Stripe public keys
            ],
            'password': [
                r'password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
                r'passwd["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
                r'pwd["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
            ],
            'secret': [
                r'secret["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']',
                r'token["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']',
                r'jwt[_-]?secret["\']?\s*[:=]\s*["\'][^"\']{16,}["\']',
            ],
            'database_url': [
                r'postgresql://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
                r'mysql://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
                r'mongodb://[^:]+:[^@]+@[^/]+/[^"\'\s]+',
            ],
            'private_key': [
                r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
                r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
            ]
        }
        
        # Vulnerability patterns
        self.vulnerability_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*["\'][^"\']*\+[^"\']*["\']',
                r'query\s*\(\s*["\'][^"\']*\+[^"\']*["\']',
                r'\.format\s*\([^)]*\)\s*["\'][^"\']*SELECT',
            ],
            'command_injection': [
                r'os\.system\s*\([^)]*\+',
                r'subprocess\.(call|run|Popen)\s*\([^)]*\+',
                r'shell=True.*\+',
            ],
            'path_traversal': [
                r'open\s*\([^)]*\.\./.*\)',
                r'file\s*\([^)]*\.\./.*\)',
                r'\.\./',
            ],
            'weak_crypto': [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'DES\s*\(',
                r'RC4\s*\(',
            ]
        }
        
        # Files to exclude from scanning
        self.exclude_patterns = [
            r'\.git/',
            r'__pycache__/',
            r'\.pyc$',
            r'node_modules/',
            r'\.env\.example$',
            r'\.log$',
            r'\.md$',
            r'\.txt$',
            r'\.json$',
            r'\.yml$',
            r'\.yaml$',
        ]
        
        # Safe patterns (to reduce false positives)
        self.safe_patterns = [
            r'env\s*\(',  # Environment variable access
            r'getenv\s*\(',  # Environment variable access
            r'Field\s*\(.*env=',  # Pydantic Field with env
            r'SecretStr',  # Pydantic SecretStr
            r'get_secret_value\(\)',  # SecretStr access
            r'# Example:',  # Comments with examples
            r'# TODO:',  # TODO comments
            r'your-.*-key',  # Placeholder values
            r'example\.com',  # Example domains
            r'localhost',  # Local development
        ]
    
    def audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit."""
        logger.info("Starting security audit...")
        
        # Scan for hardcoded secrets
        self._scan_secrets()
        
        # Scan for vulnerabilities
        self._scan_vulnerabilities()
        
        # Check file permissions
        self._check_file_permissions()
        
        # Check configuration security
        self._check_configuration_security()
        
        # Generate report
        report = self._generate_report()
        
        logger.info(f"Security audit completed. Found {len(self.findings)} issues.")
        return report
    
    def _scan_secrets(self):
        """Scan for hardcoded secrets and credentials."""
        logger.info("Scanning for hardcoded secrets...")
        
        for file_path in self._get_source_files():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Skip if line matches safe patterns
                    if any(re.search(pattern, line, re.IGNORECASE) for pattern in self.safe_patterns):
                        continue
                    
                    # Check for secret patterns
                    for category, patterns in self.secret_patterns.items():
                        for pattern in patterns:
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                self.findings.append(SecurityFinding(
                                    severity='critical',
                                    category='hardcoded_secrets',
                                    file_path=str(file_path),
                                    line_number=line_num,
                                    description=f'Potential hardcoded {category} detected',
                                    evidence=match.group(0)[:100] + '...' if len(match.group(0)) > 100 else match.group(0),
                                    recommendation=f'Move {category} to environment variables or secure configuration'
                                ))
                                
            except Exception as e:
                logger.error(f"Error scanning file {file_path}: {e}")
    
    def _scan_vulnerabilities(self):
        """Scan for common security vulnerabilities."""
        logger.info("Scanning for security vulnerabilities...")
        
        for file_path in self._get_source_files():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Check for vulnerability patterns
                    for vuln_type, patterns in self.vulnerability_patterns.items():
                        for pattern in patterns:
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                severity = 'high' if vuln_type in ['sql_injection', 'command_injection'] else 'medium'
                                self.findings.append(SecurityFinding(
                                    severity=severity,
                                    category='vulnerability',
                                    file_path=str(file_path),
                                    line_number=line_num,
                                    description=f'Potential {vuln_type.replace("_", " ")} vulnerability',
                                    evidence=match.group(0),
                                    recommendation=self._get_vulnerability_recommendation(vuln_type)
                                ))
                                
            except Exception as e:
                logger.error(f"Error scanning file {file_path}: {e}")
    
    def _check_file_permissions(self):
        """Check for insecure file permissions."""
        logger.info("Checking file permissions...")
        
        sensitive_files = [
            '.env',
            'config.py',
            'settings.py',
            'secrets.json',
            'private.key',
            'id_rsa',
        ]
        
        for file_path in self._get_all_files():
            try:
                if any(sensitive in str(file_path).lower() for sensitive in sensitive_files):
                    stat = file_path.stat()
                    mode = oct(stat.st_mode)[-3:]
                    
                    # Check if file is world-readable or world-writable
                    if mode[2] in ['4', '5', '6', '7']:  # World-readable
                        self.findings.append(SecurityFinding(
                            severity='medium',
                            category='file_permissions',
                            file_path=str(file_path),
                            line_number=0,
                            description='Sensitive file is world-readable',
                            evidence=f'File permissions: {mode}',
                            recommendation='Restrict file permissions to owner only (600 or 700)'
                        ))
                    
                    if mode[2] in ['2', '3', '6', '7']:  # World-writable
                        self.findings.append(SecurityFinding(
                            severity='high',
                            category='file_permissions',
                            file_path=str(file_path),
                            line_number=0,
                            description='Sensitive file is world-writable',
                            evidence=f'File permissions: {mode}',
                            recommendation='Remove world-write permissions immediately'
                        ))
                        
            except Exception as e:
                logger.error(f"Error checking permissions for {file_path}: {e}")
    
    def _check_configuration_security(self):
        """Check configuration files for security issues."""
        logger.info("Checking configuration security...")
        
        config_files = [
            'docker-compose.yml',
            'docker-compose.yaml',
            '.env.example',
            'config.py',
            'settings.py',
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        # Check for default passwords
                        if re.search(r'password.*=.*password', line, re.IGNORECASE):
                            self.findings.append(SecurityFinding(
                                severity='high',
                                category='default_credentials',
                                file_path=str(file_path),
                                line_number=line_num,
                                description='Default password detected',
                                evidence=line.strip(),
                                recommendation='Change default passwords before deployment'
                            ))
                        
                        # Check for debug mode in production
                        if re.search(r'debug.*=.*true', line, re.IGNORECASE):
                            self.findings.append(SecurityFinding(
                                severity='medium',
                                category='configuration',
                                file_path=str(file_path),
                                line_number=line_num,
                                description='Debug mode enabled',
                                evidence=line.strip(),
                                recommendation='Disable debug mode in production'
                            ))
                            
                except Exception as e:
                    logger.error(f"Error checking config file {file_path}: {e}")
    
    def _get_source_files(self) -> List[Path]:
        """Get list of source code files to scan."""
        source_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.sh']
        files = []
        
        for ext in source_extensions:
            files.extend(self.project_root.rglob(f'*{ext}'))
        
        # Filter out excluded files
        filtered_files = []
        for file_path in files:
            if not any(re.search(pattern, str(file_path)) for pattern in self.exclude_patterns):
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _get_all_files(self) -> List[Path]:
        """Get list of all files in the project."""
        files = []
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                if not any(re.search(pattern, str(file_path)) for pattern in self.exclude_patterns):
                    files.append(file_path)
        return files
    
    def _get_vulnerability_recommendation(self, vuln_type: str) -> str:
        """Get recommendation for specific vulnerability type."""
        recommendations = {
            'sql_injection': 'Use parameterized queries or ORM methods instead of string concatenation',
            'command_injection': 'Validate and sanitize input, avoid shell=True, use subprocess with list arguments',
            'path_traversal': 'Validate file paths, use os.path.join(), restrict access to allowed directories',
            'weak_crypto': 'Use strong cryptographic algorithms (SHA-256, AES-256, RSA-2048+)',
        }
        return recommendations.get(vuln_type, 'Review and fix the security issue')
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security audit report."""
        # Group findings by severity
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        by_category = {}
        
        for finding in self.findings:
            by_severity[finding.severity].append(finding)
            if finding.category not in by_category:
                by_category[finding.category] = []
            by_category[finding.category].append(finding)
        
        # Calculate security score
        total_issues = len(self.findings)
        critical_count = len(by_severity['critical'])
        high_count = len(by_severity['high'])
        medium_count = len(by_severity['medium'])
        low_count = len(by_severity['low'])
        
        # Security score calculation (0-100)
        security_score = max(0, 100 - (critical_count * 25) - (high_count * 10) - (medium_count * 5) - (low_count * 1))
        
        report = {
            'audit_timestamp': str(datetime.utcnow()),
            'project_root': str(self.project_root),
            'summary': {
                'total_issues': total_issues,
                'security_score': security_score,
                'critical_issues': critical_count,
                'high_issues': high_count,
                'medium_issues': medium_count,
                'low_issues': low_count,
            },
            'findings_by_severity': {
                severity: [
                    {
                        'category': f.category,
                        'file_path': f.file_path,
                        'line_number': f.line_number,
                        'description': f.description,
                        'evidence': f.evidence,
                        'recommendation': f.recommendation,
                    }
                    for f in findings
                ]
                for severity, findings in by_severity.items()
            },
            'findings_by_category': {
                category: len(findings)
                for category, findings in by_category.items()
            },
            'recommendations': self._get_general_recommendations(by_category),
        }
        
        return report
    
    def _get_general_recommendations(self, by_category: Dict) -> List[str]:
        """Get general security recommendations based on findings."""
        recommendations = []
        
        if 'hardcoded_secrets' in by_category:
            recommendations.append("Implement proper secrets management using environment variables or secret management services")
        
        if 'vulnerability' in by_category:
            recommendations.append("Conduct regular security code reviews and implement secure coding practices")
        
        if 'file_permissions' in by_category:
            recommendations.append("Review and fix file permissions for sensitive files")
        
        if 'default_credentials' in by_category:
            recommendations.append("Change all default passwords and credentials before deployment")
        
        recommendations.extend([
            "Implement automated security scanning in CI/CD pipeline",
            "Regular security training for development team",
            "Implement dependency vulnerability scanning",
            "Set up security monitoring and alerting",
        ])
        
        return recommendations

def main():
    """Main function to run security audit."""
    auditor = SecurityAuditor()
    report = auditor.audit()
    
    # Print summary
    print("\n" + "="*80)
    print("REGULENS AI SECURITY AUDIT REPORT")
    print("="*80)
    print(f"Audit Timestamp: {report['audit_timestamp']}")
    print(f"Security Score: {report['summary']['security_score']}/100")
    print(f"Total Issues: {report['summary']['total_issues']}")
    print(f"  Critical: {report['summary']['critical_issues']}")
    print(f"  High: {report['summary']['high_issues']}")
    print(f"  Medium: {report['summary']['medium_issues']}")
    print(f"  Low: {report['summary']['low_issues']}")
    
    # Print critical and high issues
    for severity in ['critical', 'high']:
        if report['findings_by_severity'][severity]:
            print(f"\n{severity.upper()} ISSUES:")
            print("-" * 40)
            for finding in report['findings_by_severity'][severity]:
                print(f"  {finding['file_path']}:{finding['line_number']}")
                print(f"    {finding['description']}")
                print(f"    Evidence: {finding['evidence']}")
                print(f"    Fix: {finding['recommendation']}")
                print()
    
    # Save detailed report
    report_file = Path("security_audit_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with error code if critical or high issues found
    if report['summary']['critical_issues'] > 0 or report['summary']['high_issues'] > 0:
        print("\n⚠️  SECURITY ISSUES DETECTED - Review and fix before production deployment!")
        return 1
    else:
        print("\n✅ No critical security issues detected.")
        return 0

if __name__ == "__main__":
    exit(main())
