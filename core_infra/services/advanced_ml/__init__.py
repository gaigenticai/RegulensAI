"""
Advanced ML Service for Phase 6 Advanced AI & Automation

This module provides enterprise-grade advanced machine learning capabilities including:
- Deep learning models with TensorFlow and PyTorch
- Reinforcement learning for optimization
- AutoML for automated model development
- Neural architecture search
- Model experimentation and tracking

Key Features:
- Multiple ML frameworks support (TensorFlow, PyTorch, scikit-learn)
- Automated hyperparameter optimization
- Model versioning and experiment tracking
- Real-time model serving and inference
- Enterprise MLOps pipeline integration
"""

from .advanced_ml_service import (
    AdvancedMLService, 
    ExperimentConfig, 
    ExperimentResult, 
    ModelPrediction,
    MLFramework,
    ExperimentType,
    ModelType,
    ExperimentStatus
)
from .deep_learning_engine import (
    DeepLearningEngine, 
    ArchitectureType, 
    OptimizationAlgorithm,
    TrainingConfig,
    ModelArchitecture
)
from .reinforcement_learning_engine import (
    ReinforcementLearningEngine, 
    RLAlgorithm, 
    EnvironmentType,
    RLConfig,
    RLTrainingResult,
    FinancialTradingEnvironment,
    DQNAgent
)
from .automl_pipeline import (
    AutoMLPipeline, 
    ModelFamily, 
    OptimizationMethod as AutoMLOptimizationMethod,
    FeatureEngineeringMethod,
    AutoMLConfig,
    ModelResult,
    AutoMLResult
)
from .experiment_tracker import (
    ExperimentTracker, 
    ExperimentStatus as TrackerExperimentStatus,
    ArtifactType,
    ExperimentMetrics,
    ExperimentArtifact,
    ExperimentRun
)
from .model_optimizer import (
    ModelOptimizer,
    OptimizationMethod,
    OptimizationObjective,
    ParameterType,
    ParameterSpace,
    OptimizationConfig,
    OptimizationResult
)

__all__ = [
    # Core service
    'AdvancedMLService',
    'ExperimentConfig',
    'ExperimentResult',
    'ModelPrediction',
    'MLFramework',
    'ExperimentType',
    'ModelType',
    'ExperimentStatus',
    
    # Deep Learning Engine
    'DeepLearningEngine',
    'ArchitectureType',
    'OptimizationAlgorithm',
    'TrainingConfig',
    'ModelArchitecture',
    
    # Reinforcement Learning Engine
    'ReinforcementLearningEngine',
    'RLAlgorithm',
    'EnvironmentType',
    'RLConfig',
    'RLTrainingResult',
    'FinancialTradingEnvironment',
    'DQNAgent',
    
    # AutoML Pipeline
    'AutoMLPipeline',
    'ModelFamily',
    'AutoMLOptimizationMethod',
    'FeatureEngineeringMethod',
    'AutoMLConfig',
    'ModelResult',
    'AutoMLResult',
    
    # Experiment Tracker
    'ExperimentTracker',
    'TrackerExperimentStatus',
    'ArtifactType',
    'ExperimentMetrics',
    'ExperimentArtifact',
    'ExperimentRun',
    
    # Model Optimizer
    'ModelOptimizer',
    'OptimizationMethod',
    'OptimizationObjective',
    'ParameterType',
    'ParameterSpace',
    'OptimizationConfig',
    'OptimizationResult'
]

__version__ = "1.0.0" 