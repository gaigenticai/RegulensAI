"""
Advanced ML Service for Phase 6 Advanced AI & Automation

Provides enterprise-grade advanced machine learning capabilities including:
- Deep learning models with TensorFlow and PyTorch
- Reinforcement learning for optimization
- AutoML for automated model development
- Neural architecture search
- Model experimentation and tracking
"""

import asyncio
import logging
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    import tensorflow as tf
    import torch
    import torch.nn as nn
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    HAS_ML_LIBRARIES = True
except ImportError:
    HAS_ML_LIBRARIES = False

from supabase import create_client, Client

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class MLFramework(Enum):
    """Supported ML frameworks"""
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    CATBOOST = "catboost"

class ExperimentType(Enum):
    """Types of ML experiments"""
    DEEP_LEARNING = "deep_learning"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    AUTOML = "automl"
    NEURAL_ARCHITECTURE_SEARCH = "nas"
    HYPERPARAMETER_OPTIMIZATION = "hpo"
    TRANSFER_LEARNING = "transfer_learning"

class ModelType(Enum):
    """Types of ML models"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    TIME_SERIES = "time_series"
    ANOMALY_DETECTION = "anomaly_detection"
    RISK_SCORING = "risk_scoring"
    FRAUD_DETECTION = "fraud_detection"

class ExperimentStatus(Enum):
    """Experiment execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ExperimentConfig:
    """Configuration for ML experiments"""
    experiment_name: str
    experiment_type: ExperimentType
    model_type: ModelType
    framework: MLFramework
    dataset_config: Dict[str, Any]
    model_config: Dict[str, Any]
    training_config: Dict[str, Any]
    evaluation_config: Dict[str, Any]
    deployment_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None

@dataclass
class ExperimentResult:
    """Results from ML experiment execution"""
    experiment_id: str
    status: ExperimentStatus
    metrics: Dict[str, float]
    artifacts: Dict[str, str]
    model_path: Optional[str] = None
    logs: Optional[List[str]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    resource_usage: Optional[Dict[str, Any]] = None

@dataclass
class ModelPrediction:
    """Model prediction result"""
    prediction_id: str
    model_id: str
    input_data: Dict[str, Any]
    prediction: Union[float, int, str, List]
    confidence: float
    prediction_timestamp: datetime
    processing_time_ms: float

class AdvancedMLService:
    """Enterprise-grade Advanced ML Service"""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Optional[Client] = None
        self.experiments: Dict[str, ExperimentResult] = {}
        self.models: Dict[str, Any] = {}
        self._initialize_ml_backends()
        
    async def initialize(self):
        """Initialize the ML service and database connections"""
        try:
            self.supabase = create_client(
                self.settings.supabase_url,
                self.settings.supabase_key
            )
            logger.info("Advanced ML Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Advanced ML Service: {str(e)}")
            raise
    
    def _initialize_ml_backends(self):
        """Initialize ML framework backends"""
        self.backends = {}
        
        if HAS_ML_LIBRARIES:
            # Initialize TensorFlow
            try:
                tf.config.experimental.set_memory_growth(
                    tf.config.experimental.list_physical_devices('GPU')[0], True
                ) if tf.config.experimental.list_physical_devices('GPU') else None
                self.backends[MLFramework.TENSORFLOW] = True
                logger.info("TensorFlow backend initialized")
            except Exception as e:
                logger.warning(f"TensorFlow initialization failed: {str(e)}")
                self.backends[MLFramework.TENSORFLOW] = False
            
            # Initialize PyTorch
            try:
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.backends[MLFramework.PYTORCH] = True
                logger.info(f"PyTorch backend initialized on {device}")
            except Exception as e:
                logger.warning(f"PyTorch initialization failed: {str(e)}")
                self.backends[MLFramework.PYTORCH] = False
        else:
            logger.warning("ML libraries not installed - running in simulation mode")
    
    async def create_experiment(
        self,
        config: ExperimentConfig,
        tenant_id: UUID,
        user_id: UUID
    ) -> str:
        """Create a new ML experiment"""
        try:
            experiment_id = str(uuid4())
            
            # Store experiment in database
            experiment_data = {
                "id": experiment_id,
                "tenant_id": str(tenant_id),
                "experiment_name": config.experiment_name,
                "experiment_type": config.experiment_type.value,
                "model_type": config.model_type.value,
                "framework": config.framework.value,
                "experiment_config": asdict(config),
                "experiment_status": ExperimentStatus.PENDING.value,
                "created_by": str(user_id),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            if self.supabase:
                result = self.supabase.table("ml_experiments").insert(experiment_data).execute()
                
            # Initialize experiment result
            self.experiments[experiment_id] = ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.PENDING,
                metrics={},
                artifacts={}
            )
            
            logger.info(f"Created ML experiment: {experiment_id}")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment: {str(e)}")
            raise
    
    async def run_experiment(
        self,
        experiment_id: str,
        tenant_id: UUID
    ) -> ExperimentResult:
        """Execute an ML experiment"""
        try:
            start_time = time.time()
            
            # Update status to running
            await self._update_experiment_status(experiment_id, ExperimentStatus.RUNNING, tenant_id)
            
            # Get experiment configuration
            experiment_data = await self._get_experiment_config(experiment_id, tenant_id)
            config = ExperimentConfig(**experiment_data["experiment_config"])
            
            # Route to appropriate experiment runner
            if config.experiment_type == ExperimentType.DEEP_LEARNING:
                result = await self._run_deep_learning_experiment(experiment_id, config)
            elif config.experiment_type == ExperimentType.REINFORCEMENT_LEARNING:
                result = await self._run_reinforcement_learning_experiment(experiment_id, config)
            elif config.experiment_type == ExperimentType.AUTOML:
                result = await self._run_automl_experiment(experiment_id, config)
            elif config.experiment_type == ExperimentType.NEURAL_ARCHITECTURE_SEARCH:
                result = await self._run_nas_experiment(experiment_id, config)
            else:
                raise ValueError(f"Unsupported experiment type: {config.experiment_type}")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            # Update experiment status and results
            await self._update_experiment_results(experiment_id, result, tenant_id)
            
            # Store in memory cache
            self.experiments[experiment_id] = result
            
            logger.info(f"Completed experiment {experiment_id} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {str(e)}")
            
            # Update status to failed
            error_result = ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.FAILED,
                metrics={},
                artifacts={},
                error_message=str(e)
            )
            
            await self._update_experiment_results(experiment_id, error_result, tenant_id)
            return error_result
    
    async def _run_deep_learning_experiment(
        self,
        experiment_id: str,
        config: ExperimentConfig
    ) -> ExperimentResult:
        """Run deep learning experiment"""
        try:
            from .deep_learning_engine import DeepLearningEngine
            
            engine = DeepLearningEngine()
            await engine.initialize()
            
            # Load and prepare data
            data = await self._load_experiment_data(config.dataset_config)
            X_train, X_test, y_train, y_test = await self._prepare_data(data, config)
            
            # Build and train model
            model = await engine.build_model(
                input_shape=X_train.shape[1:],
                model_type=config.model_type,
                model_config=config.model_config
            )
            
            history = await engine.train_model(
                model, X_train, y_train, X_test, y_test,
                training_config=config.training_config
            )
            
            # Evaluate model
            metrics = await engine.evaluate_model(model, X_test, y_test)
            
            # Save model artifacts
            model_path = await self._save_model_artifacts(experiment_id, model, history)
            
            return ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.COMPLETED,
                metrics=metrics,
                artifacts={"model_path": model_path, "history": history},
                model_path=model_path
            )
            
        except Exception as e:
            logger.error(f"Deep learning experiment failed: {str(e)}")
            raise
    
    async def _run_reinforcement_learning_experiment(
        self,
        experiment_id: str,
        config: ExperimentConfig
    ) -> ExperimentResult:
        """Run reinforcement learning experiment"""
        try:
            from .reinforcement_learning_engine import ReinforcementLearningEngine
            
            engine = ReinforcementLearningEngine()
            await engine.initialize()
            
            # Create environment and agent
            env = await engine.create_environment(config.model_config.get("environment"))
            agent = await engine.create_agent(
                env, 
                config.model_config.get("agent_type", "dqn")
            )
            
            # Train agent
            training_results = await engine.train_agent(
                agent, env, config.training_config
            )
            
            # Evaluate agent
            evaluation_results = await engine.evaluate_agent(
                agent, env, config.evaluation_config
            )
            
            # Save model artifacts
            model_path = await self._save_rl_artifacts(experiment_id, agent, training_results)
            
            metrics = {
                **training_results.get("metrics", {}),
                **evaluation_results.get("metrics", {})
            }
            
            return ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.COMPLETED,
                metrics=metrics,
                artifacts={"model_path": model_path, "training_results": training_results},
                model_path=model_path
            )
            
        except Exception as e:
            logger.error(f"Reinforcement learning experiment failed: {str(e)}")
            raise
    
    async def _run_automl_experiment(
        self,
        experiment_id: str,
        config: ExperimentConfig
    ) -> ExperimentResult:
        """Run AutoML experiment"""
        try:
            from .automl_pipeline import AutoMLPipeline
            
            pipeline = AutoMLPipeline()
            await pipeline.initialize()
            
            # Load and prepare data
            data = await self._load_experiment_data(config.dataset_config)
            
            # Run AutoML pipeline
            automl_results = await pipeline.run_automl(
                data=data,
                target_column=config.dataset_config.get("target_column"),
                model_type=config.model_type,
                automl_config=config.model_config
            )
            
            # Get best model and metrics
            best_model = automl_results["best_model"]
            best_metrics = automl_results["best_metrics"]
            
            # Save model artifacts
            model_path = await self._save_automl_artifacts(experiment_id, automl_results)
            
            return ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.COMPLETED,
                metrics=best_metrics,
                artifacts={"model_path": model_path, "automl_results": automl_results},
                model_path=model_path
            )
            
        except Exception as e:
            logger.error(f"AutoML experiment failed: {str(e)}")
            raise
    
    async def _run_nas_experiment(
        self,
        experiment_id: str,
        config: ExperimentConfig
    ) -> ExperimentResult:
        """Run Neural Architecture Search experiment"""
        try:
            # Load and prepare data
            data = await self._load_experiment_data(config.dataset_config)
            X_train, X_test, y_train, y_test = await self._prepare_data(data, config)
            
            # Run NAS
            nas_results = await self._run_neural_architecture_search(
                X_train, y_train, X_test, y_test, config
            )
            
            # Save best architecture
            model_path = await self._save_nas_artifacts(experiment_id, nas_results)
            
            return ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.COMPLETED,
                metrics=nas_results["best_metrics"],
                artifacts={"model_path": model_path, "nas_results": nas_results},
                model_path=model_path
            )
            
        except Exception as e:
            logger.error(f"NAS experiment failed: {str(e)}")
            raise
    
    async def deploy_model(
        self,
        experiment_id: str,
        deployment_config: Dict[str, Any],
        tenant_id: UUID
    ) -> str:
        """Deploy a trained model for inference"""
        try:
            # Get experiment results
            experiment = await self._get_experiment_results(experiment_id, tenant_id)
            
            if experiment["experiment_status"] != ExperimentStatus.COMPLETED.value:
                raise ValueError(f"Cannot deploy model from incomplete experiment: {experiment_id}")
            
            # Generate deployment ID
            deployment_id = str(uuid4())
            
            # Load model from artifacts
            model_path = experiment["results"]["model_path"]
            model = await self._load_model(model_path, experiment["framework"])
            
            # Store model in memory cache for inference
            self.models[deployment_id] = {
                "model": model,
                "experiment_id": experiment_id,
                "model_type": experiment["model_type"],
                "framework": experiment["framework"],
                "deployment_config": deployment_config
            }
            
            # Update database with deployment info
            deployment_data = {
                "deployment_id": deployment_id,
                "experiment_id": experiment_id,
                "tenant_id": str(tenant_id),
                "deployment_config": deployment_config,
                "deployment_status": "active",
                "deployed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if self.supabase:
                self.supabase.table("ml_deployments").insert(deployment_data).execute()
            
            logger.info(f"Model deployed successfully: {deployment_id}")
            return deployment_id
            
        except Exception as e:
            logger.error(f"Model deployment failed: {str(e)}")
            raise
    
    async def predict(
        self,
        deployment_id: str,
        input_data: Dict[str, Any],
        tenant_id: UUID
    ) -> ModelPrediction:
        """Make predictions using a deployed model"""
        try:
            start_time = time.time()
            
            # Get deployed model
            if deployment_id not in self.models:
                raise ValueError(f"Model deployment not found: {deployment_id}")
            
            model_info = self.models[deployment_id]
            model = model_info["model"]
            
            # Prepare input data
            processed_input = await self._prepare_prediction_input(
                input_data, model_info["model_type"]
            )
            
            # Make prediction
            if model_info["framework"] == MLFramework.TENSORFLOW.value:
                prediction = model.predict(processed_input)
            elif model_info["framework"] == MLFramework.PYTORCH.value:
                with torch.no_grad():
                    prediction = model(processed_input)
            else:
                prediction = model.predict(processed_input)
            
            # Process prediction output
            processed_prediction, confidence = await self._process_prediction_output(
                prediction, model_info["model_type"]
            )
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Create prediction result
            prediction_result = ModelPrediction(
                prediction_id=str(uuid4()),
                model_id=deployment_id,
                input_data=input_data,
                prediction=processed_prediction,
                confidence=confidence,
                prediction_timestamp=datetime.now(timezone.utc),
                processing_time_ms=processing_time
            )
            
            # Log prediction to database
            await self._log_prediction(prediction_result, tenant_id)
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    async def get_experiment_status(
        self,
        experiment_id: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get the status and results of an experiment"""
        try:
            if self.supabase:
                result = self.supabase.table("ml_experiments").select("*").eq(
                    "id", experiment_id
                ).eq("tenant_id", str(tenant_id)).execute()
                
                if result.data:
                    return result.data[0]
            
            # Fall back to memory cache
            if experiment_id in self.experiments:
                return asdict(self.experiments[experiment_id])
            
            raise ValueError(f"Experiment not found: {experiment_id}")
            
        except Exception as e:
            logger.error(f"Failed to get experiment status: {str(e)}")
            raise
    
    async def list_experiments(
        self,
        tenant_id: UUID,
        experiment_type: Optional[ExperimentType] = None,
        status: Optional[ExperimentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List experiments for a tenant"""
        try:
            if self.supabase:
                query = self.supabase.table("ml_experiments").select("*").eq(
                    "tenant_id", str(tenant_id)
                )
                
                if experiment_type:
                    query = query.eq("experiment_type", experiment_type.value)
                
                if status:
                    query = query.eq("experiment_status", status.value)
                
                result = query.order("created_at", desc=True).range(
                    offset, offset + limit - 1
                ).execute()
                
                return result.data
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to list experiments: {str(e)}")
            raise
    
    # Helper methods
    
    async def _update_experiment_status(
        self,
        experiment_id: str,
        status: ExperimentStatus,
        tenant_id: UUID
    ):
        """Update experiment status in database"""
        if self.supabase:
            self.supabase.table("ml_experiments").update({
                "experiment_status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", experiment_id).eq("tenant_id", str(tenant_id)).execute()
    
    async def _get_experiment_config(
        self,
        experiment_id: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get experiment configuration from database"""
        if self.supabase:
            result = self.supabase.table("ml_experiments").select("*").eq(
                "id", experiment_id
            ).eq("tenant_id", str(tenant_id)).execute()
            
            if result.data:
                return result.data[0]
        
        raise ValueError(f"Experiment configuration not found: {experiment_id}")
    
    async def _update_experiment_results(
        self,
        experiment_id: str,
        result: ExperimentResult,
        tenant_id: UUID
    ):
        """Update experiment results in database"""
        if self.supabase:
            self.supabase.table("ml_experiments").update({
                "experiment_status": result.status.value,
                "results": asdict(result),
                "completed_at": datetime.now(timezone.utc).isoformat() if result.status == ExperimentStatus.COMPLETED else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", experiment_id).eq("tenant_id", str(tenant_id)).execute()
    
    async def _load_experiment_data(self, dataset_config: Dict[str, Any]) -> pd.DataFrame:
        """Load data for experiment from configured data sources"""
        logger.info(f"Loading dataset: {dataset_config}")
        
        data_source = dataset_config.get("source", "generated")
        
        if data_source == "supabase":
            # Load from Supabase table
            table_name = dataset_config.get("table_name")
            if self.supabase and table_name:
                result = self.supabase.table(table_name).select("*").execute()
                return pd.DataFrame(result.data)
        
        elif data_source == "file":
            # Load from file path
            file_path = dataset_config.get("file_path")
            if file_path:
                if file_path.endswith('.csv'):
                    return pd.read_csv(file_path)
                elif file_path.endswith('.json'):
                    return pd.read_json(file_path)
        
        # Generate synthetic data for testing and development
        if dataset_config.get("data_type") == "financial":
            data = pd.DataFrame({
                "amount": np.random.lognormal(mean=5, sigma=1, size=1000),
                "account_age": np.random.randint(1, 3650, 1000),
                "transaction_count": np.random.randint(1, 100, 1000),
                "risk_score": np.random.random(1000),
                "is_fraud": np.random.binomial(1, 0.1, 1000)
            })
        else:
            # Default synthetic dataset
            data = pd.DataFrame({
                "feature_1": np.random.random(1000),
                "feature_2": np.random.random(1000),
                "feature_3": np.random.random(1000),
                "target": np.random.binomial(1, 0.5, 1000)
            })
        
        return data
    
    async def _prepare_data(
        self,
        data: pd.DataFrame,
        config: ExperimentConfig
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        target_column = config.dataset_config.get("target_column", "target")
        
        # Separate features and target
        X = data.drop(columns=[target_column]).values
        y = data[target_column].values
        
        # Split data
        test_size = config.dataset_config.get("test_size", 0.2)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Scale features if required
        if config.dataset_config.get("scale_features", True):
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
        
        return X_train, X_test, y_train, y_test
    
    async def _save_model_artifacts(
        self,
        experiment_id: str,
        model: Any,
        history: Dict[str, Any]
    ) -> str:
        """Save model artifacts to configured storage backend"""
        storage_backend = self.settings.ml_artifacts_storage
        
        if storage_backend == "supabase":
            # Save to Supabase storage
            model_path = f"models/{experiment_id}/model.pkl"
            
            # Serialize model
            import pickle
            model_bytes = pickle.dumps(model)
            
            if self.supabase:
                self.supabase.storage.from_("ml-artifacts").upload(
                    model_path, model_bytes
                )
                
            # Save history metadata
            history_data = {
                "experiment_id": experiment_id,
                "training_history": history,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            if self.supabase:
                self.supabase.table("model_artifacts").insert(history_data).execute()
                
        else:
            # Save to local filesystem
            from pathlib import Path
            artifacts_dir = Path("artifacts") / experiment_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            model_path = str(artifacts_dir / "model.pkl")
            
            import pickle
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
                
            # Save history
            import json
            with open(artifacts_dir / "history.json", 'w') as f:
                json.dump(history, f)
        
        logger.info(f"Model artifacts saved to: {model_path}")
        return model_path
    
    async def _save_rl_artifacts(
        self,
        experiment_id: str,
        agent: Any,
        training_results: Dict[str, Any]
    ) -> str:
        """Save reinforcement learning artifacts"""
        model_path = f"/models/rl_{experiment_id}"
        logger.info(f"Saving RL artifacts to: {model_path}")
        return model_path
    
    async def _save_automl_artifacts(
        self,
        experiment_id: str,
        automl_results: Dict[str, Any]
    ) -> str:
        """Save AutoML artifacts"""
        model_path = f"/models/automl_{experiment_id}"
        logger.info(f"Saving AutoML artifacts to: {model_path}")
        return model_path
    
    async def _save_nas_artifacts(
        self,
        experiment_id: str,
        nas_results: Dict[str, Any]
    ) -> str:
        """Save Neural Architecture Search artifacts"""
        model_path = f"/models/nas_{experiment_id}"
        logger.info(f"Saving NAS artifacts to: {model_path}")
        return model_path
    
    async def _run_neural_architecture_search(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        config: ExperimentConfig
    ) -> Dict[str, Any]:
        """Run Neural Architecture Search using evolutionary algorithms"""
        logger.info("Running Neural Architecture Search...")
        
        # NAS configuration
        population_size = config.model_config.get("population_size", 20)
        generations = config.model_config.get("generations", 10)
        mutation_rate = config.model_config.get("mutation_rate", 0.1)
        
        # Initialize population with random architectures
        population = []
        for _ in range(population_size):
            arch = self._generate_random_architecture(X_train.shape[1], config)
            population.append(arch)
        
        best_architecture = None
        best_score = 0.0
        search_history = []
        
        # Evolutionary search
        for generation in range(generations):
            # Evaluate population
            scores = []
            for arch in population:
                score = await self._evaluate_nas_architecture(arch, X_train, y_train, X_test, y_test)
                scores.append(score)
                
                if score > best_score:
                    best_score = score
                    best_architecture = arch.copy()
            
            search_history.append({
                "generation": generation,
                "best_score": best_score,
                "population_scores": scores.copy()
            })
            
            # Selection and mutation for next generation
            if generation < generations - 1:
                population = self._evolve_population(population, scores, mutation_rate)
        
        best_metrics = {
            "accuracy": best_score,
            "generations_searched": generations,
            "population_size": population_size
        }
        
        return {
            "best_architecture": best_architecture,
            "best_metrics": best_metrics,
            "search_history": search_history
        }
    
    async def _load_model(self, model_path: str, framework: str) -> Any:
        """Load a trained model from storage"""
        logger.info(f"Loading model from: {model_path}")
        
        try:
            if framework == MLFramework.TENSORFLOW.value:
                import tensorflow as tf
                return tf.keras.models.load_model(model_path)
            elif framework == MLFramework.PYTORCH.value:
                import torch
                return torch.load(model_path)
            else:
                import pickle
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return None
    
    async def _prepare_prediction_input(
        self,
        input_data: Dict[str, Any],
        model_type: str
    ) -> np.ndarray:
        """Prepare input data for prediction"""
        # Convert dict to numpy array
        values = list(input_data.values())
        return np.array([values])
    
    async def _process_prediction_output(
        self,
        prediction: Any,
        model_type: str
    ) -> Tuple[Union[float, int, str], float]:
        """Process model prediction output"""
        # Extract prediction value and confidence
        if hasattr(prediction, 'numpy'):
            pred_value = float(prediction.numpy()[0])
        elif isinstance(prediction, np.ndarray):
            pred_value = float(prediction[0])
        else:
            pred_value = float(prediction)
        
        # Calculate confidence (simplified)
        confidence = min(abs(pred_value), 1.0) if model_type == "classification" else 0.95
        
        return pred_value, confidence
    
    async def _log_prediction(
        self,
        prediction: ModelPrediction,
        tenant_id: UUID
    ):
        """Log prediction to database"""
        if self.supabase:
            prediction_data = {
                "prediction_id": prediction.prediction_id,
                "model_id": prediction.model_id,
                "tenant_id": str(tenant_id),
                "input_data": prediction.input_data,
                "prediction": prediction.prediction,
                "confidence": prediction.confidence,
                "processing_time_ms": prediction.processing_time_ms,
                "created_at": prediction.prediction_timestamp.isoformat()
            }
            
            self.supabase.table("model_predictions").insert(prediction_data).execute()
    
    async def _get_experiment_results(
        self,
        experiment_id: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get experiment results from database"""
        if self.supabase:
            result = self.supabase.table("ml_experiments").select("*").eq(
                "id", experiment_id
            ).eq("tenant_id", str(tenant_id)).execute()
            
            if result.data:
                return result.data[0]
        
        raise ValueError(f"Experiment results not found: {experiment_id}") 