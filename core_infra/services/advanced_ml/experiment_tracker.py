"""
Experiment Tracker for Advanced ML Service

Provides enterprise-grade experiment tracking capabilities including:
- Experiment versioning and management
- Metrics and artifacts tracking
- Model registry and versioning
- Performance monitoring and comparison
- Reproducibility and audit trails
"""

import logging
import json
import os
import pickle
import hashlib
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import mlflow
    import mlflow.sklearn
    import mlflow.pytorch
    import mlflow.tensorflow
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

from supabase import create_client, Client
from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    """Experiment status enumeration"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ArtifactType(Enum):
    """Types of experiment artifacts"""
    MODEL = "model"
    DATASET = "dataset"
    PLOT = "plot"
    LOG = "log"
    CONFIG = "config"
    METRICS = "metrics"
    FEATURE_IMPORTANCE = "feature_importance"

@dataclass
class ExperimentMetrics:
    """Experiment metrics container"""
    primary_metric: str
    primary_value: float
    metrics: Dict[str, float]
    validation_metrics: Optional[Dict[str, float]] = None
    test_metrics: Optional[Dict[str, float]] = None

@dataclass
class ExperimentArtifact:
    """Experiment artifact metadata"""
    artifact_id: str
    artifact_type: ArtifactType
    name: str
    path: str
    size_bytes: int
    checksum: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ExperimentRun:
    """Complete experiment run information"""
    run_id: str
    experiment_id: str
    run_name: str
    status: ExperimentStatus
    parameters: Dict[str, Any]
    metrics: ExperimentMetrics
    artifacts: List[ExperimentArtifact]
    tags: Dict[str, str]
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    source_code_version: Optional[str]
    environment_info: Dict[str, Any]
    error_message: Optional[str] = None

class ExperimentTracker:
    """Enterprise-grade Experiment Tracker"""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Optional[Client] = None
        self.active_runs: Dict[str, ExperimentRun] = {}
        self.artifacts_path = Path("artifacts")
        self.artifacts_path.mkdir(exist_ok=True)
        
    async def initialize(self):
        """Initialize the experiment tracker"""
        try:
            # Initialize Supabase connection
            self.supabase = create_client(
                self.settings.supabase_url,
                self.settings.supabase_key
            )
            
            # Initialize MLflow if available
            if HAS_MLFLOW:
                mlflow.set_tracking_uri("sqlite:///mlflow.db")
                logger.info("MLflow tracking initialized")
            
            logger.info("Experiment Tracker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Experiment Tracker: {str(e)}")
            raise
    
    async def create_experiment(
        self,
        experiment_name: str,
        description: str,
        tenant_id: UUID,
        user_id: UUID,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a new experiment"""
        try:
            experiment_id = str(uuid4())
            
            experiment_data = {
                "id": experiment_id,
                "tenant_id": str(tenant_id),
                "experiment_name": experiment_name,
                "description": description,
                "created_by": str(user_id),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tags": tags or {},
                "status": "active"
            }
            
            # Store in database
            if self.supabase:
                self.supabase.table("ml_experiments").insert(experiment_data).execute()
            
            # Create MLflow experiment if available
            if HAS_MLFLOW:
                mlflow.create_experiment(experiment_name, artifact_location=str(self.artifacts_path / experiment_id))
            
            logger.info(f"Created experiment: {experiment_name} ({experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment: {str(e)}")
            raise
    
    async def start_run(
        self,
        experiment_id: str,
        run_name: str,
        parameters: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None,
        tenant_id: Optional[UUID] = None
    ) -> str:
        """Start a new experiment run"""
        try:
            run_id = str(uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Collect environment information
            environment_info = await self._collect_environment_info()
            
            # Create run object
            experiment_run = ExperimentRun(
                run_id=run_id,
                experiment_id=experiment_id,
                run_name=run_name,
                status=ExperimentStatus.RUNNING,
                parameters=parameters,
                metrics=ExperimentMetrics(
                    primary_metric="",
                    primary_value=0.0,
                    metrics={}
                ),
                artifacts=[],
                tags=tags or {},
                start_time=start_time,
                end_time=None,
                duration=None,
                source_code_version=None,
                environment_info=environment_info
            )
            
            # Store in memory
            self.active_runs[run_id] = experiment_run
            
            # Store in database
            if self.supabase:
                run_data = {
                    "id": run_id,
                    "experiment_id": experiment_id,
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "run_name": run_name,
                    "status": ExperimentStatus.RUNNING.value,
                    "parameters": parameters,
                    "tags": tags or {},
                    "start_time": start_time.isoformat(),
                    "environment_info": environment_info
                }
                self.supabase.table("experiment_runs").insert(run_data).execute()
            
            # Start MLflow run if available
            if HAS_MLFLOW:
                mlflow.start_run(run_name=run_name)
                mlflow.log_params(parameters)
                if tags:
                    mlflow.set_tags(tags)
            
            logger.info(f"Started experiment run: {run_name} ({run_id})")
            return run_id
            
        except Exception as e:
            logger.error(f"Failed to start experiment run: {str(e)}")
            raise
    
    async def log_metric(
        self,
        run_id: str,
        metric_name: str,
        value: float,
        step: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ):
        """Log a metric for an experiment run"""
        try:
            if run_id not in self.active_runs:
                raise ValueError(f"Run {run_id} not found or not active")
            
            run = self.active_runs[run_id]
            run.metrics.metrics[metric_name] = value
            
            # Update primary metric if not set
            if not run.metrics.primary_metric:
                run.metrics.primary_metric = metric_name
                run.metrics.primary_value = value
            
            # Log to MLflow if available
            if HAS_MLFLOW and mlflow.active_run():
                mlflow.log_metric(metric_name, value, step)
            
            # Store in database
            if self.supabase:
                metric_data = {
                    "run_id": run_id,
                    "metric_name": metric_name,
                    "value": value,
                    "step": step,
                    "logged_at": (timestamp or datetime.now(timezone.utc)).isoformat()
                }
                self.supabase.table("experiment_metrics").insert(metric_data).execute()
            
            logger.debug(f"Logged metric {metric_name}={value} for run {run_id}")
            
        except Exception as e:
            logger.error(f"Failed to log metric: {str(e)}")
            raise
    
    async def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ):
        """Log multiple metrics at once"""
        for metric_name, value in metrics.items():
            await self.log_metric(run_id, metric_name, value, step)
    
    async def log_parameter(
        self,
        run_id: str,
        param_name: str,
        value: Any
    ):
        """Log a parameter for an experiment run"""
        try:
            if run_id not in self.active_runs:
                raise ValueError(f"Run {run_id} not found or not active")
            
            run = self.active_runs[run_id]
            run.parameters[param_name] = value
            
            # Log to MLflow if available
            if HAS_MLFLOW and mlflow.active_run():
                mlflow.log_param(param_name, value)
            
            logger.debug(f"Logged parameter {param_name}={value} for run {run_id}")
            
        except Exception as e:
            logger.error(f"Failed to log parameter: {str(e)}")
            raise
    
    async def log_artifact(
        self,
        run_id: str,
        artifact_path: str,
        artifact_type: ArtifactType,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an artifact for an experiment run"""
        try:
            if run_id not in self.active_runs:
                raise ValueError(f"Run {run_id} not found or not active")
            
            # Generate artifact ID
            artifact_id = str(uuid4())
            
            # Copy artifact to storage
            artifact_name = name or Path(artifact_path).name
            stored_path = self.artifacts_path / run_id / artifact_name
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Calculate checksum
            checksum = await self._calculate_checksum(artifact_path)
            
            # Get file size
            size_bytes = Path(artifact_path).stat().st_size if Path(artifact_path).exists() else 0
            
            # Create artifact object
            artifact = ExperimentArtifact(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                name=artifact_name,
                path=str(stored_path),
                size_bytes=size_bytes,
                checksum=checksum,
                created_at=datetime.now(timezone.utc),
                metadata=metadata
            )
            
            # Add to run
            run = self.active_runs[run_id]
            run.artifacts.append(artifact)
            
            # Log to MLflow if available
            if HAS_MLFLOW and mlflow.active_run():
                mlflow.log_artifact(artifact_path)
            
            # Store in database
            if self.supabase:
                artifact_data = {
                    "id": artifact_id,
                    "run_id": run_id,
                    "artifact_type": artifact_type.value,
                    "name": artifact_name,
                    "path": str(stored_path),
                    "size_bytes": size_bytes,
                    "checksum": checksum,
                    "metadata": metadata or {},
                    "created_at": artifact.created_at.isoformat()
                }
                self.supabase.table("experiment_artifacts").insert(artifact_data).execute()
            
            logger.info(f"Logged artifact {artifact_name} for run {run_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Failed to log artifact: {str(e)}")
            raise
    
    async def log_model(
        self,
        run_id: str,
        model: Any,
        model_name: str,
        framework: str = "sklearn",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a trained model as an artifact"""
        try:
            # Save model to temporary file
            model_dir = self.artifacts_path / run_id / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"{model_name}.pkl"
            
            # Save model
            if framework.lower() == "sklearn":
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
            elif framework.lower() == "tensorflow" and HAS_MLFLOW:
                mlflow.tensorflow.log_model(model, model_name)
            elif framework.lower() == "pytorch" and HAS_MLFLOW:
                mlflow.pytorch.log_model(model, model_name)
            else:
                # Default pickle serialization
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
            
            # Log as artifact
            model_metadata = {
                "framework": framework,
                "model_type": type(model).__name__,
                **(metadata or {})
            }
            
            artifact_id = await self.log_artifact(
                run_id,
                str(model_path),
                ArtifactType.MODEL,
                f"{model_name}.pkl",
                model_metadata
            )
            
            logger.info(f"Logged model {model_name} for run {run_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Failed to log model: {str(e)}")
            raise
    
    async def end_run(
        self,
        run_id: str,
        status: ExperimentStatus = ExperimentStatus.COMPLETED,
        error_message: Optional[str] = None
    ):
        """End an experiment run"""
        try:
            if run_id not in self.active_runs:
                raise ValueError(f"Run {run_id} not found or not active")
            
            run = self.active_runs[run_id]
            end_time = datetime.now(timezone.utc)
            duration = (end_time - run.start_time).total_seconds()
            
            # Update run status
            run.status = status
            run.end_time = end_time
            run.duration = duration
            run.error_message = error_message
            
            # Update database
            if self.supabase:
                update_data = {
                    "status": status.value,
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "metrics": asdict(run.metrics),
                    "error_message": error_message
                }
                self.supabase.table("experiment_runs").update(update_data).eq("id", run_id).execute()
            
            # End MLflow run if available
            if HAS_MLFLOW and mlflow.active_run():
                mlflow.end_run(status="FINISHED" if status == ExperimentStatus.COMPLETED else "FAILED")
            
            # Remove from active runs
            del self.active_runs[run_id]
            
            logger.info(f"Ended experiment run {run_id} with status {status.value}")
            
        except Exception as e:
            logger.error(f"Failed to end experiment run: {str(e)}")
            raise
    
    async def get_experiment_runs(
        self,
        experiment_id: str,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get experiment runs for an experiment"""
        try:
            if self.supabase:
                result = self.supabase.table("experiment_runs").select("*").eq(
                    "experiment_id", experiment_id
                ).eq("tenant_id", str(tenant_id)).order(
                    "start_time", desc=True
                ).range(offset, offset + limit - 1).execute()
                
                return result.data
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get experiment runs: {str(e)}")
            raise
    
    async def get_run_details(
        self,
        run_id: str,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific run"""
        try:
            # Check active runs first
            if run_id in self.active_runs:
                return asdict(self.active_runs[run_id])
            
            # Query database
            if self.supabase:
                run_result = self.supabase.table("experiment_runs").select("*").eq(
                    "id", run_id
                ).eq("tenant_id", str(tenant_id)).execute()
                
                if not run_result.data:
                    return None
                
                run_data = run_result.data[0]
                
                # Get metrics
                metrics_result = self.supabase.table("experiment_metrics").select("*").eq(
                    "run_id", run_id
                ).execute()
                
                # Get artifacts
                artifacts_result = self.supabase.table("experiment_artifacts").select("*").eq(
                    "run_id", run_id
                ).execute()
                
                run_data["metrics_history"] = metrics_result.data
                run_data["artifacts"] = artifacts_result.data
                
                return run_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get run details: {str(e)}")
            raise
    
    async def compare_runs(
        self,
        run_ids: List[str],
        tenant_id: UUID,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compare multiple experiment runs"""
        try:
            comparison_data = {
                "runs": [],
                "metrics_comparison": {},
                "parameters_comparison": {},
                "summary": {}
            }
            
            for run_id in run_ids:
                run_details = await self.get_run_details(run_id, tenant_id)
                if run_details:
                    comparison_data["runs"].append(run_details)
            
            if not comparison_data["runs"]:
                return comparison_data
            
            # Compare metrics
            all_metrics = set()
            for run in comparison_data["runs"]:
                if "metrics" in run:
                    all_metrics.update(run["metrics"].get("metrics", {}).keys())
            
            filter_metrics = metrics or list(all_metrics)
            
            for metric in filter_metrics:
                comparison_data["metrics_comparison"][metric] = []
                for run in comparison_data["runs"]:
                    value = run.get("metrics", {}).get("metrics", {}).get(metric)
                    comparison_data["metrics_comparison"][metric].append({
                        "run_id": run["id"],
                        "run_name": run["run_name"],
                        "value": value
                    })
            
            # Compare parameters
            all_params = set()
            for run in comparison_data["runs"]:
                all_params.update(run.get("parameters", {}).keys())
            
            for param in all_params:
                comparison_data["parameters_comparison"][param] = []
                for run in comparison_data["runs"]:
                    value = run.get("parameters", {}).get(param)
                    comparison_data["parameters_comparison"][param].append({
                        "run_id": run["id"],
                        "run_name": run["run_name"],
                        "value": value
                    })
            
            # Generate summary
            comparison_data["summary"] = {
                "total_runs": len(comparison_data["runs"]),
                "metrics_compared": len(filter_metrics),
                "parameters_compared": len(all_params)
            }
            
            return comparison_data
            
        except Exception as e:
            logger.error(f"Failed to compare runs: {str(e)}")
            raise
    
    async def get_best_run(
        self,
        experiment_id: str,
        tenant_id: UUID,
        metric_name: str,
        maximize: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get the best run for an experiment based on a metric"""
        try:
            runs = await self.get_experiment_runs(experiment_id, tenant_id, limit=1000)
            
            if not runs:
                return None
            
            best_run = None
            best_value = float('-inf') if maximize else float('inf')
            
            for run in runs:
                metrics = run.get("metrics", {}).get("metrics", {})
                if metric_name in metrics:
                    value = metrics[metric_name]
                    if (maximize and value > best_value) or (not maximize and value < best_value):
                        best_value = value
                        best_run = run
            
            return best_run
            
        except Exception as e:
            logger.error(f"Failed to get best run: {str(e)}")
            raise
    
    # Helper methods
    
    async def _collect_environment_info(self) -> Dict[str, Any]:
        """Collect environment information"""
        import platform
        import sys
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        
        if Path(file_path).exists():
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest() 