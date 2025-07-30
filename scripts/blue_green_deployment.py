#!/usr/bin/env python3
"""
Blue-Green Deployment Script for RegulensAI.
Implements zero-downtime deployment strategy with automated rollback capabilities.
"""

import asyncio
import argparse
import json
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import subprocess
import structlog
import yaml
import requests

logger = structlog.get_logger(__name__)


class BlueGreenDeployment:
    """
    Manages blue-green deployments for RegulensAI platform.
    """
    
    def __init__(self, namespace: str = "regulensai", kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.services = ["api", "notifications", "integrations", "worker"]
        self.health_check_timeout = 300  # 5 minutes
        self.traffic_switch_delay = 30  # 30 seconds
        
    async def deploy(
        self,
        image_tag: str,
        environment: str = "production",
        dry_run: bool = False,
        skip_health_checks: bool = False
    ) -> bool:
        """
        Execute blue-green deployment.
        """
        try:
            logger.info(f"Starting blue-green deployment for tag {image_tag}")
            
            # Step 1: Determine current and new colors
            current_color = await self._get_current_color()
            new_color = "green" if current_color == "blue" else "blue"
            
            logger.info(f"Current color: {current_color}, New color: {new_color}")
            
            if dry_run:
                logger.info("DRY RUN: Would deploy new version with the following steps:")
                await self._log_deployment_plan(new_color, image_tag, environment)
                return True
            
            # Step 2: Deploy new version
            deployment_success = await self._deploy_new_version(
                new_color, image_tag, environment
            )
            
            if not deployment_success:
                logger.error("Failed to deploy new version")
                return False
            
            # Step 3: Health checks
            if not skip_health_checks:
                health_check_success = await self._perform_health_checks(new_color)
                
                if not health_check_success:
                    logger.error("Health checks failed, rolling back")
                    await self._cleanup_failed_deployment(new_color)
                    return False
            
            # Step 4: Switch traffic
            traffic_switch_success = await self._switch_traffic(new_color)
            
            if not traffic_switch_success:
                logger.error("Failed to switch traffic, rolling back")
                await self._rollback_traffic(current_color)
                await self._cleanup_failed_deployment(new_color)
                return False
            
            # Step 5: Verify new deployment
            verification_success = await self._verify_deployment(new_color)
            
            if not verification_success:
                logger.error("Deployment verification failed, rolling back")
                await self._rollback_traffic(current_color)
                await self._cleanup_failed_deployment(new_color)
                return False
            
            # Step 6: Cleanup old deployment
            await self._cleanup_old_deployment(current_color)
            
            logger.info(f"Blue-green deployment completed successfully. Active color: {new_color}")
            return True
            
        except Exception as e:
            logger.error(f"Blue-green deployment failed: {e}")
            return False
    
    async def rollback(self, target_color: Optional[str] = None) -> bool:
        """
        Rollback to previous deployment.
        """
        try:
            logger.info("Starting rollback process")
            
            if target_color:
                rollback_color = target_color
            else:
                # Determine rollback target
                current_color = await self._get_current_color()
                rollback_color = "green" if current_color == "blue" else "blue"
            
            # Check if rollback target exists
            if not await self._deployment_exists(rollback_color):
                logger.error(f"Rollback target {rollback_color} does not exist")
                return False
            
            # Switch traffic back
            traffic_switch_success = await self._switch_traffic(rollback_color)
            
            if not traffic_switch_success:
                logger.error("Failed to switch traffic during rollback")
                return False
            
            # Verify rollback
            verification_success = await self._verify_deployment(rollback_color)
            
            if not verification_success:
                logger.error("Rollback verification failed")
                return False
            
            logger.info(f"Rollback completed successfully. Active color: {rollback_color}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    async def status(self) -> Dict[str, Any]:
        """
        Get current deployment status.
        """
        try:
            current_color = await self._get_current_color()
            
            status = {
                "current_color": current_color,
                "timestamp": datetime.utcnow().isoformat(),
                "deployments": {}
            }
            
            # Check both blue and green deployments
            for color in ["blue", "green"]:
                deployment_info = await self._get_deployment_info(color)
                status["deployments"][color] = deployment_info
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {"error": str(e)}
    
    async def _get_current_color(self) -> str:
        """Get the currently active color."""
        try:
            # Check service selector to determine active color
            cmd = [
                "kubectl", "get", "service", "regulensai-api",
                "-n", self.namespace,
                "-o", "jsonpath={.spec.selector.color}"
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            color = result.stdout.strip()
            
            return color if color in ["blue", "green"] else "blue"
            
        except subprocess.CalledProcessError:
            # Default to blue if no color is set
            return "blue"
    
    async def _deploy_new_version(self, color: str, image_tag: str, environment: str) -> bool:
        """Deploy new version with specified color."""
        try:
            logger.info(f"Deploying {color} version with tag {image_tag}")
            
            # Prepare Helm values for the new deployment
            values_file = f"./helm/regulensai/values-{environment}.yaml"
            
            # Create temporary values file with color-specific settings
            temp_values = await self._create_color_specific_values(
                color, image_tag, environment
            )
            
            # Deploy using Helm
            cmd = [
                "helm", "upgrade", "--install", f"regulensai-{color}",
                "./helm/regulensai",
                "--namespace", self.namespace,
                "--create-namespace",
                "--values", values_file,
                "--values", temp_values,
                "--wait", "--timeout=15m"
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Helm deployment failed: {result.stderr}")
                return False
            
            logger.info(f"Successfully deployed {color} version")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy new version: {e}")
            return False
    
    async def _create_color_specific_values(
        self, color: str, image_tag: str, environment: str
    ) -> str:
        """Create color-specific Helm values file."""
        try:
            values = {
                "deployment": {
                    "color": color
                },
                "image": {
                    "tag": image_tag
                },
                "environment": environment,
                "nameOverride": f"regulensai-{color}",
                "fullnameOverride": f"regulensai-{color}",
                "service": {
                    "nameOverride": f"regulensai-{color}"
                }
            }
            
            # Write to temporary file
            temp_file = f"/tmp/values-{color}-{int(time.time())}.yaml"
            with open(temp_file, 'w') as f:
                yaml.dump(values, f)
            
            return temp_file
            
        except Exception as e:
            logger.error(f"Failed to create color-specific values: {e}")
            raise
    
    async def _perform_health_checks(self, color: str) -> bool:
        """Perform comprehensive health checks on new deployment."""
        try:
            logger.info(f"Performing health checks for {color} deployment")
            
            # Wait for pods to be ready
            for service in self.services:
                if not await self._wait_for_pods_ready(color, service):
                    return False
            
            # Perform application health checks
            if not await self._check_application_health(color):
                return False
            
            # Perform integration tests
            if not await self._run_integration_tests(color):
                return False
            
            logger.info(f"All health checks passed for {color} deployment")
            return True
            
        except Exception as e:
            logger.error(f"Health checks failed: {e}")
            return False
    
    async def _wait_for_pods_ready(self, color: str, service: str) -> bool:
        """Wait for pods to be ready."""
        try:
            logger.info(f"Waiting for {service} pods to be ready ({color})")
            
            cmd = [
                "kubectl", "wait", "--for=condition=ready",
                f"pod", "-l", f"app.kubernetes.io/name=regulensai,app.kubernetes.io/component={service},color={color}",
                "-n", self.namespace,
                f"--timeout={self.health_check_timeout}s"
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Pods not ready for {service}: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to wait for pods: {e}")
            return False
    
    async def _check_application_health(self, color: str) -> bool:
        """Check application health endpoints."""
        try:
            logger.info(f"Checking application health for {color} deployment")
            
            # Get service endpoints
            endpoints = await self._get_service_endpoints(color)
            
            for service, endpoint in endpoints.items():
                health_url = f"http://{endpoint}/health"
                
                # Retry health check with exponential backoff
                for attempt in range(5):
                    try:
                        response = requests.get(health_url, timeout=10)
                        
                        if response.status_code == 200:
                            logger.info(f"Health check passed for {service}")
                            break
                        else:
                            logger.warning(f"Health check failed for {service}: {response.status_code}")
                    
                    except requests.RequestException as e:
                        logger.warning(f"Health check request failed for {service}: {e}")
                    
                    if attempt < 4:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Health check failed for {service} after all retries")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            return False
    
    async def _run_integration_tests(self, color: str) -> bool:
        """Run integration tests against new deployment."""
        try:
            logger.info(f"Running integration tests for {color} deployment")
            
            # Run smoke tests
            cmd = [
                "python", "scripts/smoke_tests.py",
                "--environment", "production",
                "--color", color,
                "--namespace", self.namespace
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Integration tests failed: {result.stderr}")
                return False
            
            logger.info("Integration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run integration tests: {e}")
            return False
    
    async def _switch_traffic(self, new_color: str) -> bool:
        """Switch traffic to new deployment."""
        try:
            logger.info(f"Switching traffic to {new_color} deployment")
            
            # Update service selectors to point to new color
            for service in self.services:
                cmd = [
                    "kubectl", "patch", "service", f"regulensai-{service}",
                    "-n", self.namespace,
                    "-p", f'{{"spec":{{"selector":{{"color":"{new_color}"}}}}}}'
                ]
                
                if self.kubeconfig:
                    cmd.extend(["--kubeconfig", self.kubeconfig])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to update service {service}: {result.stderr}")
                    return False
            
            # Wait for traffic to stabilize
            logger.info(f"Waiting {self.traffic_switch_delay}s for traffic to stabilize")
            await asyncio.sleep(self.traffic_switch_delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch traffic: {e}")
            return False
    
    async def _verify_deployment(self, color: str) -> bool:
        """Verify deployment is working correctly."""
        try:
            logger.info(f"Verifying {color} deployment")
            
            # Run production verification tests
            cmd = [
                "python", "scripts/production_verification.py",
                "--environment", "production",
                "--color", color
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Production verification failed: {result.stderr}")
                return False
            
            logger.info("Production verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify deployment: {e}")
            return False
    
    async def _rollback_traffic(self, rollback_color: str) -> bool:
        """Rollback traffic to previous deployment."""
        try:
            logger.info(f"Rolling back traffic to {rollback_color}")
            return await self._switch_traffic(rollback_color)
            
        except Exception as e:
            logger.error(f"Failed to rollback traffic: {e}")
            return False
    
    async def _cleanup_failed_deployment(self, color: str) -> bool:
        """Cleanup failed deployment."""
        try:
            logger.info(f"Cleaning up failed {color} deployment")
            
            cmd = [
                "helm", "uninstall", f"regulensai-{color}",
                "-n", self.namespace
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            subprocess.run(cmd, capture_output=True, text=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup deployment: {e}")
            return False
    
    async def _cleanup_old_deployment(self, old_color: str) -> bool:
        """Cleanup old deployment after successful switch."""
        try:
            logger.info(f"Cleaning up old {old_color} deployment")
            
            # Wait a bit before cleanup to ensure stability
            await asyncio.sleep(60)
            
            cmd = [
                "helm", "uninstall", f"regulensai-{old_color}",
                "-n", self.namespace
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Failed to cleanup old deployment: {result.stderr}")
                # Don't fail the deployment for cleanup issues
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cleanup old deployment: {e}")
            return True  # Don't fail deployment for cleanup issues
    
    async def _deployment_exists(self, color: str) -> bool:
        """Check if deployment exists."""
        try:
            cmd = [
                "kubectl", "get", "deployment", f"regulensai-{color}-api",
                "-n", self.namespace
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception:
            return False
    
    async def _get_deployment_info(self, color: str) -> Dict[str, Any]:
        """Get deployment information."""
        try:
            info = {
                "exists": await self._deployment_exists(color),
                "services": {}
            }
            
            if info["exists"]:
                for service in self.services:
                    service_info = await self._get_service_info(color, service)
                    info["services"][service] = service_info
            
            return info
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_service_info(self, color: str, service: str) -> Dict[str, Any]:
        """Get service information."""
        try:
            cmd = [
                "kubectl", "get", "deployment", f"regulensai-{color}-{service}",
                "-n", self.namespace,
                "-o", "json"
            ]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                deployment_data = json.loads(result.stdout)
                return {
                    "replicas": deployment_data["spec"]["replicas"],
                    "ready_replicas": deployment_data["status"].get("readyReplicas", 0),
                    "image": deployment_data["spec"]["template"]["spec"]["containers"][0]["image"]
                }
            else:
                return {"error": "Deployment not found"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_service_endpoints(self, color: str) -> Dict[str, str]:
        """Get service endpoints for health checks."""
        # This would need to be implemented based on your service discovery mechanism
        # For now, return placeholder endpoints
        return {
            "api": f"regulensai-{color}-api:8000",
            "notifications": f"regulensai-{color}-notifications:8001",
            "integrations": f"regulensai-{color}-integrations:8002"
        }
    
    async def _log_deployment_plan(self, color: str, image_tag: str, environment: str):
        """Log deployment plan for dry run."""
        plan = [
            f"1. Deploy {color} version with image tag: {image_tag}",
            f"2. Wait for all pods to be ready",
            f"3. Perform health checks on {color} deployment",
            f"4. Run integration tests",
            f"5. Switch traffic from current to {color}",
            f"6. Verify {color} deployment",
            f"7. Cleanup old deployment"
        ]
        
        for step in plan:
            logger.info(f"DRY RUN: {step}")


async def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Blue-Green Deployment for RegulensAI")
    parser.add_argument("action", choices=["deploy", "rollback", "status"], help="Action to perform")
    parser.add_argument("--image-tag", help="Image tag to deploy")
    parser.add_argument("--environment", default="production", help="Environment to deploy to")
    parser.add_argument("--namespace", default="regulensai", help="Kubernetes namespace")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run")
    parser.add_argument("--skip-health-checks", action="store_true", help="Skip health checks")
    parser.add_argument("--target-color", help="Target color for rollback")
    
    args = parser.parse_args()
    
    deployment = BlueGreenDeployment(
        namespace=args.namespace,
        kubeconfig=args.kubeconfig
    )
    
    if args.action == "deploy":
        if not args.image_tag:
            logger.error("Image tag is required for deployment")
            sys.exit(1)
        
        success = await deployment.deploy(
            image_tag=args.image_tag,
            environment=args.environment,
            dry_run=args.dry_run,
            skip_health_checks=args.skip_health_checks
        )
        
        sys.exit(0 if success else 1)
    
    elif args.action == "rollback":
        success = await deployment.rollback(target_color=args.target_color)
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        status = await deployment.status()
        print(json.dumps(status, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
