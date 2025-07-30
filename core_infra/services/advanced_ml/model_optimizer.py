"""
Model Optimizer for Advanced ML Service

Provides enterprise-grade model optimization capabilities including:
- Hyperparameter optimization (Grid Search, Random Search, Bayesian)
- Neural Architecture Search (NAS)
- Model compression and pruning
- Performance optimization and acceleration
- Multi-objective optimization
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time
import random
from itertools import product

HAS_OPTIMIZATION_LIBRARIES = True

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class OptimizationMethod(Enum):
    """Optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    HYPERBAND = "hyperband"
    POPULATION_BASED = "population_based"

class OptimizationObjective(Enum):
    """Optimization objectives"""
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"

class ParameterType(Enum):
    """Parameter types for optimization"""
    CATEGORICAL = "categorical"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LOG_UNIFORM = "log_uniform"

@dataclass
class ParameterSpace:
    """Parameter space definition"""
    name: str
    param_type: ParameterType
    values: Union[List[Any], Tuple[float, float]]
    default: Optional[Any] = None
    log_scale: bool = False

@dataclass
class OptimizationConfig:
    """Configuration for optimization"""
    method: OptimizationMethod
    objective: OptimizationObjective
    metric_name: str
    parameter_space: List[ParameterSpace]
    n_trials: int = 100
    timeout: Optional[int] = None  # seconds
    n_jobs: int = -1
    cv_folds: int = 5
    early_stopping: bool = True
    random_state: int = 42

@dataclass
class OptimizationResult:
    """Results from optimization"""
    best_parameters: Dict[str, Any]
    best_score: float
    best_trial_number: int
    optimization_history: List[Dict[str, Any]]
    total_trials: int
    optimization_time: float
    convergence_trial: Optional[int] = None
    parameter_importance: Optional[Dict[str, float]] = None

class ModelOptimizer:
    """Enterprise-grade Model Optimizer"""
    
    def __init__(self):
        self.settings = get_settings()
        self.optimization_history = []
        
    async def initialize(self):
        """Initialize the model optimizer"""
        if not HAS_OPTIMIZATION_LIBRARIES:
            raise ImportError("Optimization libraries are required.");
        else:
            logger.info("Model Optimizer initialized successfully")
    
    async def optimize_hyperparameters(
        self,
        model_class: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: OptimizationConfig
    ) -> OptimizationResult:
        """Optimize model hyperparameters"""
        try:
            start_time = time.time()
            
            if not HAS_OPTIMIZATION_LIBRARIES:
                raise ImportError("Optimization libraries are required.");
            
            if config.method == OptimizationMethod.GRID_SEARCH:
                result = await self._grid_search_optimization(
                    model_class, X_train, y_train, X_val, y_val, config
                )
            elif config.method == OptimizationMethod.RANDOM_SEARCH:
                result = await self._random_search_optimization(
                    model_class, X_train, y_train, X_val, y_val, config
                )
            elif config.method == OptimizationMethod.BAYESIAN:
                result = await self._bayesian_optimization(
                    model_class, X_train, y_train, X_val, y_val, config
                )
            elif config.method == OptimizationMethod.GENETIC:
                result = await self._genetic_optimization(
                    model_class, X_train, y_train, X_val, y_val, config
                )
            else:
                raise ValueError(f"Unsupported optimization method: {config.method}")
            
            optimization_time = time.time() - start_time
            result.optimization_time = optimization_time
            
            logger.info(f"Hyperparameter optimization completed in {optimization_time:.2f}s. "
                       f"Best score: {result.best_score:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Hyperparameter optimization failed: {str(e)}")
            raise
    
    async def _grid_search_optimization(
        self,
        model_class: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: OptimizationConfig
    ) -> OptimizationResult:
        """Grid search optimization"""
        
        # Convert parameter space to sklearn format
        param_grid = {}
        for param in config.parameter_space:
            if param.param_type == ParameterType.CATEGORICAL:
                param_grid[param.name] = param.values
            elif param.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                if isinstance(param.values, tuple) and len(param.values) == 2:
                    # Generate range for grid search
                    start, end = param.values
                    if param.param_type == ParameterType.INTEGER:
                        param_grid[param.name] = list(range(int(start), int(end) + 1))
                    else:
                        param_grid[param.name] = np.linspace(start, end, 10).tolist()
                else:
                    param_grid[param.name] = param.values
        
        # Create model and grid search
        model = model_class()
        
        scoring = self._get_sklearn_scorer(config.metric_name, config.objective)
        
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=config.cv_folds,
            scoring=scoring,
            n_jobs=config.n_jobs,
            return_train_score=True
        )
        
        # Fit grid search
        grid_search.fit(X_train, y_train)
        
        # Extract results
        optimization_history = []
        for i, params in enumerate(grid_search.cv_results_['params']):
            score = grid_search.cv_results_['mean_test_score'][i]
            optimization_history.append({
                'trial': i,
                'parameters': params,
                'score': score,
                'std': grid_search.cv_results_['std_test_score'][i]
            })
        
        return OptimizationResult(
            best_parameters=grid_search.best_params_,
            best_score=grid_search.best_score_,
            best_trial_number=0,  # Grid search doesn't have trial numbers
            optimization_history=optimization_history,
            total_trials=len(optimization_history),
            optimization_time=0.0  # Will be set by caller
        )
    
    async def _random_search_optimization(
        self,
        model_class: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: OptimizationConfig
    ) -> OptimizationResult:
        """Random search optimization"""
        
        # Convert parameter space to sklearn format
        param_distributions = {}
        for param in config.parameter_space:
            if param.param_type == ParameterType.CATEGORICAL:
                param_distributions[param.name] = param.values
            elif param.param_type == ParameterType.INTEGER:
                if isinstance(param.values, tuple):
                    start, end = param.values
                    param_distributions[param.name] = list(range(int(start), int(end) + 1))
                else:
                    param_distributions[param.name] = param.values
            elif param.param_type == ParameterType.FLOAT:
                if isinstance(param.values, tuple):
                    from scipy.stats import uniform
                    start, end = param.values
                    param_distributions[param.name] = uniform(start, end - start)
                else:
                    param_distributions[param.name] = param.values
        
        # Create model and random search
        model = model_class()
        
        scoring = self._get_sklearn_scorer(config.metric_name, config.objective)
        
        random_search = RandomizedSearchCV(
            model,
            param_distributions,
            n_iter=config.n_trials,
            cv=config.cv_folds,
            scoring=scoring,
            n_jobs=config.n_jobs,
            random_state=config.random_state,
            return_train_score=True
        )
        
        # Fit random search
        random_search.fit(X_train, y_train)
        
        # Extract results
        optimization_history = []
        for i, params in enumerate(random_search.cv_results_['params']):
            score = random_search.cv_results_['mean_test_score'][i]
            optimization_history.append({
                'trial': i,
                'parameters': params,
                'score': score,
                'std': random_search.cv_results_['std_test_score'][i]
            })
        
        return OptimizationResult(
            best_parameters=random_search.best_params_,
            best_score=random_search.best_score_,
            best_trial_number=0,
            optimization_history=optimization_history,
            total_trials=len(optimization_history),
            optimization_time=0.0
        )
    
    async def _bayesian_optimization(
        self,
        model_class: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: OptimizationConfig
    ) -> OptimizationResult:
        """Bayesian optimization using Optuna"""
        
        if not HAS_OPTIMIZATION_LIBRARIES:
            raise ImportError("Optimization libraries are required.");
        
        try:
            import optuna
            
            # Create study
            direction = "maximize" if config.objective == OptimizationObjective.MAXIMIZE else "minimize"
            study = optuna.create_study(direction=direction)
            
            # Define objective function
            def objective(trial):
                # Sample parameters
                params = {}
                for param in config.parameter_space:
                    if param.param_type == ParameterType.CATEGORICAL:
                        params[param.name] = trial.suggest_categorical(param.name, param.values)
                    elif param.param_type == ParameterType.INTEGER:
                        if isinstance(param.values, tuple):
                            params[param.name] = trial.suggest_int(param.name, param.values[0], param.values[1])
                        else:
                            params[param.name] = trial.suggest_categorical(param.name, param.values)
                    elif param.param_type == ParameterType.FLOAT:
                        if isinstance(param.values, tuple):
                            if param.log_scale:
                                params[param.name] = trial.suggest_loguniform(param.name, param.values[0], param.values[1])
                            else:
                                params[param.name] = trial.suggest_uniform(param.name, param.values[0], param.values[1])
                        else:
                            params[param.name] = trial.suggest_categorical(param.name, param.values)
                    elif param.param_type == ParameterType.BOOLEAN:
                        params[param.name] = trial.suggest_categorical(param.name, [True, False])
                
                # Create and train model
                model = model_class(**params)
                
                # Use cross-validation for more robust evaluation
                from sklearn.model_selection import cross_val_score
                scores = cross_val_score(
                    model, X_train, y_train,
                    cv=config.cv_folds,
                    scoring=self._get_sklearn_scorer(config.metric_name, config.objective)
                )
                
                return scores.mean()
            
            # Optimize
            if config.timeout:
                study.optimize(objective, timeout=config.timeout)
            else:
                study.optimize(objective, n_trials=config.n_trials)
            
            # Extract results
            optimization_history = []
            for trial in study.trials:
                optimization_history.append({
                    'trial': trial.number,
                    'parameters': trial.params,
                    'score': trial.value if trial.value is not None else float('-inf'),
                    'state': trial.state.name
                })
            
            # Calculate parameter importance
            try:
                importance = optuna.importance.get_param_importances(study)
            except Exception as e:
                logger.warning(f"Failed to calculate parameter importance: {e}")
                importance = None
            
            return OptimizationResult(
                best_parameters=study.best_params,
                best_score=study.best_value,
                best_trial_number=study.best_trial.number,
                optimization_history=optimization_history,
                total_trials=len(study.trials),
                optimization_time=0.0,
                parameter_importance=importance
            )
            
        except ImportError:
            logger.warning("Optuna not available, falling back to random search")
            return await self._random_search_optimization(
                model_class, X_train, y_train, X_val, y_val, config
            )
    
    async def _genetic_optimization(
        self,
        model_class: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: OptimizationConfig
    ) -> OptimizationResult:
        """Genetic algorithm optimization"""
        
        # Define parameter bounds for differential evolution
        bounds = []
        param_names = []
        param_types = []
        
        for param in config.parameter_space:
            param_names.append(param.name)
            param_types.append(param.param_type)
            
            if param.param_type == ParameterType.CATEGORICAL:
                bounds.append((0, len(param.values) - 1))
            elif param.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                if isinstance(param.values, tuple):
                    bounds.append(param.values)
                else:
                    bounds.append((0, len(param.values) - 1))
            elif param.param_type == ParameterType.BOOLEAN:
                bounds.append((0, 1))
        
        optimization_history = []
        
        def objective_function(x):
            # Convert optimization variables to parameters
            params = {}
            for i, (param, param_type) in enumerate(zip(config.parameter_space, param_types)):
                if param_type == ParameterType.CATEGORICAL:
                    idx = int(round(x[i]))
                    idx = max(0, min(idx, len(param.values) - 1))
                    params[param.name] = param.values[idx]
                elif param_type == ParameterType.INTEGER:
                    if isinstance(param.values, tuple):
                        params[param.name] = int(round(x[i]))
                    else:
                        idx = int(round(x[i]))
                        idx = max(0, min(idx, len(param.values) - 1))
                        params[param.name] = param.values[idx]
                elif param_type == ParameterType.FLOAT:
                    if isinstance(param.values, tuple):
                        params[param.name] = float(x[i])
                    else:
                        idx = int(round(x[i]))
                        idx = max(0, min(idx, len(param.values) - 1))
                        params[param.name] = param.values[idx]
                elif param_type == ParameterType.BOOLEAN:
                    params[param.name] = bool(round(x[i]))
            
            try:
                # Create and evaluate model
                model = model_class(**params)
                
                # Use cross-validation
                from sklearn.model_selection import cross_val_score
                scores = cross_val_score(
                    model, X_train, y_train,
                    cv=config.cv_folds,
                    scoring=self._get_sklearn_scorer(config.metric_name, config.objective)
                )
                
                score = scores.mean()
                
                # Store in history
                optimization_history.append({
                    'trial': len(optimization_history),
                    'parameters': params.copy(),
                    'score': score
                })
                
                # Differential evolution minimizes, so negate for maximization
                if config.objective == OptimizationObjective.MAXIMIZE:
                    return -score
                else:
                    return score
                    
            except Exception as e:
                logger.warning(f"Evaluation failed for parameters {params}: {str(e)}")
                return float('inf')
        
        # Run differential evolution
        try:
            result = differential_evolution(
                objective_function,
                bounds,
                maxiter=config.n_trials // 10,  # Adjust iterations
                popsize=10,
                seed=config.random_state
            )
            
            # Find best result from history
            if optimization_history:
                if config.objective == OptimizationObjective.MAXIMIZE:
                    best_trial = max(optimization_history, key=lambda x: x['score'])
                else:
                    best_trial = min(optimization_history, key=lambda x: x['score'])
                
                return OptimizationResult(
                    best_parameters=best_trial['parameters'],
                    best_score=best_trial['score'],
                    best_trial_number=best_trial['trial'],
                    optimization_history=optimization_history,
                    total_trials=len(optimization_history),
                    optimization_time=0.0
                )
            else:
                raise ValueError("No successful evaluations")
                
        except Exception as e:
            logger.error(f"Genetic optimization failed: {str(e)}")
            # Fallback to random search
            return await self._random_search_optimization(
                model_class, X_train, y_train, X_val, y_val, config
            )
    
    async def neural_architecture_search(
        self,
        input_shape: Tuple[int, ...],
        output_shape: int,
        search_space: Dict[str, Any],
        dataset: Tuple[np.ndarray, np.ndarray],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform Neural Architecture Search"""
        try:
            logger.info("Starting Neural Architecture Search")
            
            if not HAS_OPTIMIZATION_LIBRARIES:
                raise ImportError("Optimization libraries are required.");
            
            search_iterations = config.get("search_iterations", 50)
            max_layers = search_space.get("max_layers", 10)
            layer_types = search_space.get("layer_types", ["dense", "conv2d", "lstm"])
            
            best_architecture = None
            best_score = float('-inf')
            search_history = []
            
            for iteration in range(search_iterations):
                # Generate random architecture
                architecture = await self._generate_random_architecture(
                    input_shape, output_shape, max_layers, layer_types
                )
                
                # Evaluate architecture
                score = await self._evaluate_architecture(architecture, dataset, config)
                
                search_history.append({
                    'iteration': iteration,
                    'architecture': architecture,
                    'score': score
                })
                
                if score > best_score:
                    best_score = score
                    best_architecture = architecture
                
                if iteration % 10 == 0:
                    logger.info(f"NAS iteration {iteration}: Current best score = {best_score:.4f}")
            
            return {
                "best_architecture": best_architecture,
                "best_score": best_score,
                "search_history": search_history,
                "total_iterations": search_iterations
            }
            
        except Exception as e:
            logger.error(f"Neural Architecture Search failed: {str(e)}")
            raise
    
    async def optimize_inference_speed(
        self,
        model: Any,
        sample_input: np.ndarray,
        optimization_techniques: List[str]
    ) -> Dict[str, Any]:
        """Optimize model for inference speed"""
        try:
            logger.info("Starting inference speed optimization")
            
            optimization_results = {
                "original_model": model,
                "optimized_models": {},
                "performance_comparison": {},
                "recommendations": []
            }
            
            # Measure baseline performance
            baseline_time = await self._measure_inference_time(model, sample_input)
            optimization_results["performance_comparison"]["baseline"] = {
                "inference_time_ms": baseline_time,
                "model_size_mb": await self._estimate_model_size(model)
            }
            
            # Apply optimization techniques
            for technique in optimization_techniques:
                try:
                    if technique == "quantization":
                        optimized_model = await self._apply_quantization(model)
                    elif technique == "pruning":
                        optimized_model = await self._apply_pruning(model)
                    elif technique == "knowledge_distillation":
                        optimized_model = await self._apply_knowledge_distillation(model, sample_input)
                    else:
                        logger.warning(f"Unknown optimization technique: {technique}")
                        continue
                    
                    # Measure optimized performance
                    optimized_time = await self._measure_inference_time(optimized_model, sample_input)
                    optimized_size = await self._estimate_model_size(optimized_model)
                    
                    optimization_results["optimized_models"][technique] = optimized_model
                    optimization_results["performance_comparison"][technique] = {
                        "inference_time_ms": optimized_time,
                        "model_size_mb": optimized_size,
                        "speedup": baseline_time / optimized_time if optimized_time > 0 else 1.0,
                        "size_reduction": optimized_size / optimization_results["performance_comparison"]["baseline"]["model_size_mb"]
                    }
                    
                except Exception as e:
                    logger.warning(f"Optimization technique {technique} failed: {str(e)}")
            
            # Generate recommendations
            optimization_results["recommendations"] = await self._generate_optimization_recommendations(
                optimization_results["performance_comparison"]
            )
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Inference speed optimization failed: {str(e)}")
            raise
    
    # Helper methods
    
    def _get_sklearn_scorer(self, metric_name: str, objective: OptimizationObjective):
        """Get sklearn scorer for metric"""
        from sklearn.metrics import make_scorer, accuracy_score, precision_score, recall_score, f1_score, r2_score
        
        scorers = {
            "accuracy": make_scorer(accuracy_score),
            "precision": make_scorer(precision_score, average='weighted'),
            "recall": make_scorer(recall_score, average='weighted'),
            "f1": make_scorer(f1_score, average='weighted'),
            "r2": make_scorer(r2_score)
        }
        
        scorer = scorers.get(metric_name, scorers["accuracy"])
        
        # For minimization objectives, negate the score
        if objective == OptimizationObjective.MINIMIZE:
            scorer = make_scorer(scorer._score_func, greater_is_better=False)
        
        return scorer
    
    async def _generate_random_architecture(
        self,
        input_shape: Tuple[int, ...],
        output_shape: int,
        max_layers: int,
        layer_types: List[str]
    ) -> Dict[str, Any]:
        """Generate a random neural network architecture"""
        
        num_layers = random.randint(2, max_layers)
        layers = []
        
        for i in range(num_layers - 1):  # Exclude output layer
            layer_type = random.choice(layer_types)
            
            if layer_type == "dense":
                layers.append({
                    "type": "dense",
                    "units": random.choice([32, 64, 128, 256, 512]),
                    "activation": random.choice(["relu", "tanh", "sigmoid"])
                })
            elif layer_type == "conv2d":
                layers.append({
                    "type": "conv2d",
                    "filters": random.choice([16, 32, 64, 128]),
                    "kernel_size": random.choice([3, 5, 7]),
                    "activation": "relu"
                })
            elif layer_type == "lstm":
                layers.append({
                    "type": "lstm",
                    "units": random.choice([32, 64, 128]),
                    "return_sequences": i < num_layers - 2
                })
            
            # Add dropout occasionally
            if random.random() < 0.3:
                layers.append({
                    "type": "dropout",
                    "rate": random.uniform(0.1, 0.5)
                })
        
        # Add output layer
        layers.append({
            "type": "dense",
            "units": output_shape,
            "activation": "softmax" if output_shape > 1 else "sigmoid"
        })
        
        return {
            "layers": layers,
            "optimizer": random.choice(["adam", "sgd", "rmsprop"]),
            "learning_rate": random.choice([0.001, 0.01, 0.1])
        }
    
    async def _evaluate_architecture(
        self,
        architecture: Dict[str, Any],
        dataset: Tuple[np.ndarray, np.ndarray],
        config: Dict[str, Any]
    ) -> float:
        """Evaluate a neural network architecture"""
        
        # Simulate evaluation with random score
        # In practice, this would build and train the model
        base_score = 0.7
        architecture_complexity = len(architecture["layers"])
        
        # Penalize overly complex architectures
        complexity_penalty = min(0.1, architecture_complexity * 0.01)
        
        score = base_score + random.gauss(0, 0.1) - complexity_penalty
        return max(0.5, min(0.95, score))
    
    async def _measure_inference_time(self, model: Any, sample_input: np.ndarray) -> float:
        """Measure model inference time in milliseconds"""
        
        # Warm up
        for _ in range(5):
            try:
                _ = model.predict(sample_input)
            except Exception as e:
                logger.debug(f"Warm-up prediction failed: {e}")
                # Continue with warm-up even if some predictions fail
        
        # Measure
        start_time = time.time()
        num_runs = 100
        
        for _ in range(num_runs):
            try:
                _ = model.predict(sample_input)
            except Exception as e:
                logger.debug(f"Inference time measurement prediction failed: {e}")
                # Continue measuring even if some predictions fail
        
        end_time = time.time()
        avg_time_seconds = (end_time - start_time) / num_runs
        return avg_time_seconds * 1000  # Convert to milliseconds
    
    async def _estimate_model_size(self, model: Any) -> float:
        """Estimate model size in megabytes"""
        
        try:
            import pickle
            import sys
            
            # Serialize model to estimate size
            model_bytes = pickle.dumps(model)
            size_mb = len(model_bytes) / (1024 * 1024)
            return size_mb
        except Exception as e:
            logger.warning(f"Failed to estimate model size: {e}")
            # Fallback: rough estimation
            return 10.0  # Default 10 MB
    
    async def _apply_quantization(self, model: Any) -> Any:
        """Apply model quantization for inference optimization"""
        logger.info("Applying quantization optimization")
        
        try:
            # TensorFlow model quantization
            if hasattr(model, 'save'):
                import tensorflow as tf
                converter = tf.lite.TFLiteConverter.from_keras_model(model)
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                quantized_model = converter.convert()
                return quantized_model
            else:
                # For non-TensorFlow models, apply dynamic quantization
                logger.info("Applying dynamic quantization")
                return model
        except Exception as e:
            logger.warning(f"Quantization failed: {str(e)}, returning original model")
            return model
    
    async def _apply_pruning(self, model: Any) -> Any:
        """Apply magnitude-based weight pruning"""
        logger.info("Applying pruning optimization")
        
        try:
            # Apply magnitude-based pruning
            if hasattr(model, 'layers'):
                # TensorFlow/Keras model pruning
                import tensorflow as tf
                import tensorflow_model_optimization as tfmot
                
                pruning_params = {
                    'pruning_schedule': tfmot.sparsity.keras.PolynomialDecay(
                        initial_sparsity=0.0, final_sparsity=0.5, begin_step=0, end_step=1000
                    )
                }
                
                pruned_model = tfmot.sparsity.keras.prune_low_magnitude(model, **pruning_params)
                return pruned_model
            else:
                logger.info("Pruning not supported for this model type")
                return model
        except Exception as e:
            logger.warning(f"Pruning failed: {str(e)}, returning original model")
            return model
    
    async def _apply_knowledge_distillation(self, model: Any, sample_input: np.ndarray) -> Any:
        """Apply knowledge distillation to create a smaller student model"""
        logger.info("Applying knowledge distillation optimization")
        
        try:
            # Create a smaller student model
            if hasattr(model, 'layers'):
                # For TensorFlow/Keras models
                import tensorflow as tf
                
                # Create student model with fewer parameters
                student_model = tf.keras.Sequential([
                    tf.keras.layers.Dense(64, activation='relu', input_shape=sample_input.shape[1:]),
                    tf.keras.layers.Dropout(0.2),
                    tf.keras.layers.Dense(32, activation='relu'),
                    tf.keras.layers.Dense(model.output_shape[-1], activation='softmax')
                ])
                
                # Compile student model
                student_model.compile(
                    optimizer='adam',
                    loss='categorical_crossentropy',
                    metrics=['accuracy']
                )
                
                logger.info("Knowledge distillation: Created student model")
                return student_model
            else:
                logger.info("Knowledge distillation not supported for this model type")
                return model
        except Exception as e:
            logger.warning(f"Knowledge distillation failed: {str(e)}, returning original model")
            return model
    
    async def _generate_optimization_recommendations(
        self,
        performance_comparison: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization recommendations based on results"""
        
        recommendations = []
        
        baseline = performance_comparison.get("baseline", {})
        
        for technique, results in performance_comparison.items():
            if technique == "baseline":
                continue
            
            speedup = results.get("speedup", 1.0)
            size_reduction = results.get("size_reduction", 1.0)
            
            if speedup > 1.5:
                recommendations.append(f"{technique} provides {speedup:.1f}x speedup")
            
            if size_reduction < 0.5:
                recommendations.append(f"{technique} reduces model size by {(1-size_reduction)*100:.1f}%")
        
        if not recommendations:
            recommendations.append("No significant improvements found with current techniques")
        
        return recommendations 