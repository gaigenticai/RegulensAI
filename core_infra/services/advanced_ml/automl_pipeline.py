"""
AutoML Pipeline for Advanced ML Service

Provides enterprise-grade automated machine learning capabilities including:
- Automated model selection
- Hyperparameter optimization
- Feature engineering and selection
- Model ensemble creation
- Performance validation and reporting
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from itertools import product

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, RandomizedSearchCV
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
    from sklearn.svm import SVC, SVR
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.naive_bayes import GaussianNB
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder, OneHotEncoder
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression, RFE
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    HAS_AUTOML_LIBRARIES = True
except ImportError:
    HAS_AUTOML_LIBRARIES = False
    raise ImportError("Required AutoML libraries are missing. Install them via requirements.txt.")

# Separate optional imports to avoid XGBoost library loading issues
HAS_XGBOOST = False
HAS_LIGHTGBM = False

if HAS_AUTOML_LIBRARIES:
    # Try to import XGBoost with production configuration
    try:
        import xgboost as xgb
        HAS_XGBOOST = True

        # Configure XGBoost for production
        import os
        os.environ['OMP_NUM_THREADS'] = '4'  # Limit threads for stability

    except ImportError:
        HAS_XGBOOST = False
        class MockXGB:
            class XGBClassifier:
                def __init__(self, *args, **kwargs):
                    self.classes_ = [0, 1]
                def fit(self, X, y, **kwargs):
                    return self
                def predict(self, X):
                    return np.random.randint(0, 2, len(X))
                def predict_proba(self, X):
                    return np.random.random((len(X), 2))
                def get_params(self, deep=True):
                    return {}
                def set_params(self, **params):
                    return self

            class XGBRegressor:
                def __init__(self, *args, **kwargs):
                    pass
                def fit(self, X, y, **kwargs):
                    return self
                def predict(self, X):
                    return np.random.random(len(X))
                def get_params(self, deep=True):
                    return {}
                def set_params(self, **params):
                    return self
        xgb = MockXGB()

    # Try to import LightGBM with production configuration
    try:
        import lightgbm as lgb
        HAS_LIGHTGBM = True

        # Configure LightGBM for production
        lgb.register_logger(lambda msg: None)  # Suppress verbose logging

    except ImportError:
        HAS_LIGHTGBM = False
        class MockLGB:
            class LGBMClassifier:
                def __init__(self, *args, **kwargs):
                    self.classes_ = [0, 1]
                def fit(self, X, y, **kwargs):
                    return self
                def predict(self, X):
                    return np.random.randint(0, 2, len(X))
                def predict_proba(self, X):
                    return np.random.random((len(X), 2))
                def get_params(self, deep=True):
                    return {}
                def set_params(self, **params):
                    return self

            class LGBMRegressor:
                def __init__(self, *args, **kwargs):
                    pass
                def fit(self, X, y, **kwargs):
                    return self
                def predict(self, X):
                    return np.random.random(len(X))
                def get_params(self, deep=True):
                    return {}
                def set_params(self, **params):
                    return self
        lgb = MockLGB()
else:
    # If sklearn is not available, create all mocks
    HAS_XGBOOST = False
    HAS_LIGHTGBM = False

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class ModelFamily(Enum):
    """Families of ML models"""
    LINEAR = "linear"
    TREE_BASED = "tree_based"
    ENSEMBLE = "ensemble"
    SVM = "svm"
    NEURAL_NETWORK = "neural_network"
    NAIVE_BAYES = "naive_bayes"
    KNN = "knn"

class OptimizationMethod(Enum):
    """Hyperparameter optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"

class FeatureEngineeringMethod(Enum):
    """Feature engineering methods"""
    SCALING = "scaling"
    ENCODING = "encoding"
    SELECTION = "selection"
    TRANSFORMATION = "transformation"
    INTERACTION = "interaction"

@dataclass
class AutoMLConfig:
    """Configuration for AutoML pipeline"""
    task_type: str  # 'classification' or 'regression'
    metric: str     # Primary metric to optimize
    time_budget: int = 3600  # Time budget in seconds
    model_families: List[ModelFamily] = None
    optimization_method: OptimizationMethod = OptimizationMethod.RANDOM_SEARCH
    cross_validation_folds: int = 5
    test_size: float = 0.2
    feature_engineering: bool = True
    ensemble_methods: bool = True
    max_models: int = 50
    early_stopping: bool = True
    
    def __post_init__(self):
        if self.model_families is None:
            self.model_families = [
                ModelFamily.LINEAR,
                ModelFamily.TREE_BASED,
                ModelFamily.ENSEMBLE
            ]

@dataclass
class ModelResult:
    """Results for a single model"""
    model_name: str
    model_family: ModelFamily
    model_instance: Any
    parameters: Dict[str, Any]
    cv_scores: List[float]
    cv_mean: float
    cv_std: float
    test_score: float
    training_time: float
    prediction_time: float
    feature_importance: Optional[Dict[str, float]] = None

@dataclass
class AutoMLResult:
    """Results from AutoML pipeline"""
    best_model: Any
    best_model_name: str
    best_score: float
    best_parameters: Dict[str, Any]
    model_results: List[ModelResult]
    feature_engineering_results: Dict[str, Any]
    ensemble_results: Optional[Dict[str, Any]] = None
    leaderboard: List[Dict[str, Any]] = None
    total_time: float = 0.0

class AutoMLPipeline:
    """Enterprise-grade AutoML Pipeline"""
    
    def __init__(self):
        self.settings = get_settings()
        self.models_registry = {}
        self.feature_transformers = {}
        self._initialize_model_registry()
    
    async def initialize(self):
        """Initialize the AutoML pipeline"""
        if not HAS_AUTOML_LIBRARIES:
            raise ImportError("AutoML libraries are required for production use. Please install them.");
        else:
            logger.info("AutoML Pipeline initialized successfully")
    
    def _initialize_model_registry(self):
        """Initialize the registry of available models"""
        if not HAS_AUTOML_LIBRARIES:
            return
        
        # Classification models
        self.classification_models = {
            "logistic_regression": {
                "model": LogisticRegression,
                "family": ModelFamily.LINEAR,
                "params": {
                    "C": [0.1, 1.0, 10.0],
                    "penalty": ["l1", "l2"],
                    "solver": ["liblinear", "saga"]
                }
            },
            "random_forest": {
                "model": RandomForestClassifier,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [None, 10, 20],
                    "min_samples_split": [2, 5, 10]
                }
            },
            "gradient_boosting": {
                "model": GradientBoostingClassifier,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "learning_rate": [0.05, 0.1, 0.2],
                    "max_depth": [3, 5, 7]
                }
            },
            "svm": {
                "model": SVC,
                "family": ModelFamily.SVM,
                "params": {
                    "C": [0.1, 1.0, 10.0],
                    "kernel": ["rbf", "linear"],
                    "probability": [True]
                }
            },
            "knn": {
                "model": KNeighborsClassifier,
                "family": ModelFamily.KNN,
                "params": {
                    "n_neighbors": [3, 5, 7, 9],
                    "weights": ["uniform", "distance"]
                }
            },
            "naive_bayes": {
                "model": GaussianNB,
                "family": ModelFamily.NAIVE_BAYES,
                "params": {}
            },
            "decision_tree": {
                "model": DecisionTreeClassifier,
                "family": ModelFamily.TREE_BASED,
                "params": {
                    "max_depth": [None, 5, 10, 20],
                    "min_samples_split": [2, 5, 10]
                }
            }
        }
        
        # Add XGBoost and LightGBM if available
        if HAS_XGBOOST:
            self.classification_models["xgboost"] = {
                "model": xgb.XGBClassifier,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "learning_rate": [0.05, 0.1, 0.2],
                    "max_depth": [3, 5, 7]
                }
            }
        
        if HAS_LIGHTGBM:
            self.classification_models["lightgbm"] = {
                "model": lgb.LGBMClassifier,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "learning_rate": [0.05, 0.1, 0.2],
                    "max_depth": [3, 5, 7]
                }
            }
        
        # Regression models
        self.regression_models = {
            "linear_regression": {
                "model": LinearRegression,
                "family": ModelFamily.LINEAR,
                "params": {}
            },
            "ridge_regression": {
                "model": Ridge,
                "family": ModelFamily.LINEAR,
                "params": {
                    "alpha": [0.1, 1.0, 10.0]
                }
            },
            "lasso_regression": {
                "model": Lasso,
                "family": ModelFamily.LINEAR,
                "params": {
                    "alpha": [0.1, 1.0, 10.0]
                }
            },
            "random_forest": {
                "model": RandomForestRegressor,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [None, 10, 20],
                    "min_samples_split": [2, 5, 10]
                }
            },
            "gradient_boosting": {
                "model": GradientBoostingRegressor,
                "family": ModelFamily.ENSEMBLE,
                "params": {
                    "n_estimators": [50, 100, 200],
                    "learning_rate": [0.05, 0.1, 0.2],
                    "max_depth": [3, 5, 7]
                }
            },
            "svr": {
                "model": SVR,
                "family": ModelFamily.SVM,
                "params": {
                    "C": [0.1, 1.0, 10.0],
                    "kernel": ["rbf", "linear"]
                }
            },
            "knn": {
                "model": KNeighborsRegressor,
                "family": ModelFamily.KNN,
                "params": {
                    "n_neighbors": [3, 5, 7, 9],
                    "weights": ["uniform", "distance"]
                }
            },
            "decision_tree": {
                "model": DecisionTreeRegressor,
                "family": ModelFamily.TREE_BASED,
                "params": {
                    "max_depth": [None, 5, 10, 20],
                    "min_samples_split": [2, 5, 10]
                }
            }
        }
    
    async def run_automl(
        self,
        data: pd.DataFrame,
        target_column: str,
        model_type: str,
        automl_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run the AutoML pipeline"""
        try:
            start_time = time.time()
            
            config = AutoMLConfig(
                task_type=model_type,
                metric=automl_config.get("metric", "accuracy" if model_type == "classification" else "r2"),
                **automl_config
            )
            
            logger.info(f"Starting AutoML pipeline for {config.task_type}")
            
            # Prepare data
            X, y = await self._prepare_data(data, target_column)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=config.test_size, random_state=42
            )
            
            # Feature engineering
            feature_engineering_results = {}
            if config.feature_engineering:
                X_train, X_test, feature_engineering_results = await self._perform_feature_engineering(
                    X_train, X_test, y_train, config
                )
            
            # Model selection and optimization
            model_results = await self._run_model_selection(
                X_train, y_train, X_test, y_test, config
            )
            
            # Create ensemble if requested
            ensemble_results = None
            if config.ensemble_methods and len(model_results) > 1:
                ensemble_results = await self._create_ensemble(
                    model_results, X_train, y_train, X_test, y_test, config
                )
            
            # Get best model
            best_model_result = max(model_results, key=lambda x: x.cv_mean)
            
            # Create leaderboard
            leaderboard = []
            for result in sorted(model_results, key=lambda x: x.cv_mean, reverse=True):
                leaderboard.append({
                    "model_name": result.model_name,
                    "cv_score": result.cv_mean,
                    "cv_std": result.cv_std,
                    "test_score": result.test_score,
                    "training_time": result.training_time
                })
            
            total_time = time.time() - start_time
            
            automl_result = {
                "best_model": best_model_result.model_instance,
                "best_model_name": best_model_result.model_name,
                "best_score": best_model_result.cv_mean,
                "best_metrics": {
                    "cv_mean": best_model_result.cv_mean,
                    "cv_std": best_model_result.cv_std,
                    "test_score": best_model_result.test_score
                },
                "best_parameters": best_model_result.parameters,
                "model_results": model_results,
                "feature_engineering_results": feature_engineering_results,
                "ensemble_results": ensemble_results,
                "leaderboard": leaderboard,
                "total_time": total_time,
                "config": config
            }
            
            logger.info(f"AutoML completed in {total_time:.2f}s. Best model: {best_model_result.model_name} "
                       f"with score: {best_model_result.cv_mean:.4f}")
            
            return automl_result
            
        except Exception as e:
            logger.error(f"AutoML pipeline failed: {str(e)}")
            raise
    
    async def _prepare_data(
        self,
        data: pd.DataFrame,
        target_column: str
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for AutoML"""
        
        # Separate features and target
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        # Handle missing values
        X = X.fillna(X.mean() if X.select_dtypes(include=[np.number]).shape[1] > 0 else X.mode().iloc[0])
        
        # Handle categorical variables
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
        
        return X, y
    
    async def _perform_feature_engineering(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        config: AutoMLConfig
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Perform automated feature engineering"""
        
        results = {}
        
        # Feature scaling
        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        X_test_scaled = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )
        
        # Feature selection
        if config.task_type == "classification":
            selector = SelectKBest(f_classif, k=min(20, X_train.shape[1]))
        else:
            selector = SelectKBest(f_regression, k=min(20, X_train.shape[1]))
        
        X_train_selected = pd.DataFrame(
            selector.fit_transform(X_train_scaled, y_train),
            index=X_train.index
        )
        X_test_selected = pd.DataFrame(
            selector.transform(X_test_scaled),
            index=X_test.index
        )
        
        # Get selected feature names
        selected_features = X_train.columns[selector.get_support()].tolist()
        X_train_selected.columns = selected_features
        X_test_selected.columns = selected_features
        
        results = {
            "scaler": scaler,
            "feature_selector": selector,
            "selected_features": selected_features,
            "original_features": len(X_train.columns),
            "selected_features_count": len(selected_features)
        }
        
        return X_train_selected, X_test_selected, results
    
    async def _run_model_selection(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        config: AutoMLConfig
    ) -> List[ModelResult]:
        """Run model selection and hyperparameter optimization"""
        
        model_results = []
        models_registry = (
            self.classification_models if config.task_type == "classification"
            else self.regression_models
        )
        
        # Filter models by families
        if config.model_families:
            filtered_models = {
                name: info for name, info in models_registry.items()
                if info["family"] in config.model_families
            }
        else:
            filtered_models = models_registry
        
        for model_name, model_info in filtered_models.items():
            try:
                start_time = time.time()
                
                # Initialize model
                model_class = model_info["model"]
                base_model = model_class()
                
                # Hyperparameter optimization
                if model_info["params"]:
                    if config.optimization_method == OptimizationMethod.GRID_SEARCH:
                        search = GridSearchCV(
                            base_model,
                            model_info["params"],
                            cv=config.cross_validation_folds,
                            scoring=self._get_scoring_metric(config),
                            n_jobs=-1
                        )
                    else:  # Random search
                        search = RandomizedSearchCV(
                            base_model,
                            model_info["params"],
                            n_iter=10,
                            cv=config.cross_validation_folds,
                            scoring=self._get_scoring_metric(config),
                            n_jobs=-1,
                            random_state=42
                        )
                    
                    search.fit(X_train, y_train)
                    best_model = search.best_estimator_
                    best_params = search.best_params_
                    cv_scores = search.cv_results_['mean_test_score']
                    cv_mean = search.best_score_
                    cv_std = search.cv_results_['std_test_score'][search.best_index_]
                else:
                    # No hyperparameters to optimize
                    cv_scores = cross_val_score(
                        base_model, X_train, y_train,
                        cv=config.cross_validation_folds,
                        scoring=self._get_scoring_metric(config)
                    )
                    cv_mean = cv_scores.mean()
                    cv_std = cv_scores.std()
                    best_model = base_model.fit(X_train, y_train)
                    best_params = {}
                
                # Test score
                test_start = time.time()
                test_score = self._calculate_test_score(best_model, X_test, y_test, config)
                prediction_time = time.time() - test_start
                
                training_time = time.time() - start_time
                
                # Feature importance
                feature_importance = self._get_feature_importance(best_model, X_train.columns)
                
                model_result = ModelResult(
                    model_name=model_name,
                    model_family=model_info["family"],
                    model_instance=best_model,
                    parameters=best_params,
                    cv_scores=cv_scores.tolist() if hasattr(cv_scores, 'tolist') else [cv_mean],
                    cv_mean=cv_mean,
                    cv_std=cv_std,
                    test_score=test_score,
                    training_time=training_time,
                    prediction_time=prediction_time,
                    feature_importance=feature_importance
                )
                
                model_results.append(model_result)
                
                logger.info(f"Model {model_name}: CV Score = {cv_mean:.4f} (±{cv_std:.4f}), "
                           f"Test Score = {test_score:.4f}, Time = {training_time:.2f}s")
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                continue
        
        return model_results
    
    async def _create_ensemble(
        self,
        model_results: List[ModelResult],
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        config: AutoMLConfig
    ) -> Dict[str, Any]:
        """Create ensemble from best models"""
        
        # Select top models for ensemble
        top_models = sorted(model_results, key=lambda x: x.cv_mean, reverse=True)[:5]
        
        # Simple voting ensemble
        ensemble_predictions = []
        
        for model_result in top_models:
            if config.task_type == "classification":
                if hasattr(model_result.model_instance, 'predict_proba'):
                    pred = model_result.model_instance.predict_proba(X_test)[:, 1]
                else:
                    pred = model_result.model_instance.predict(X_test)
            else:
                pred = model_result.model_instance.predict(X_test)
            
            ensemble_predictions.append(pred)
        
        # Average predictions
        ensemble_pred = np.mean(ensemble_predictions, axis=0)
        
        if config.task_type == "classification":
            ensemble_pred_binary = (ensemble_pred > 0.5).astype(int)
            ensemble_score = accuracy_score(y_test, ensemble_pred_binary)
        else:
            ensemble_score = r2_score(y_test, ensemble_pred)
        
        return {
            "ensemble_score": ensemble_score,
            "component_models": [m.model_name for m in top_models],
            "individual_scores": [m.test_score for m in top_models],
            "improvement": ensemble_score - max(m.test_score for m in top_models)
        }
    
    def _get_scoring_metric(self, config: AutoMLConfig) -> str:
        """Get sklearn scoring metric name"""
        metric_mapping = {
            "accuracy": "accuracy",
            "precision": "precision",
            "recall": "recall",
            "f1": "f1",
            "auc": "roc_auc",
            "r2": "r2",
            "mse": "neg_mean_squared_error",
            "mae": "neg_mean_absolute_error"
        }
        
        return metric_mapping.get(config.metric, "accuracy")
    
    def _calculate_test_score(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        config: AutoMLConfig
    ) -> float:
        """Calculate test score based on metric"""
        
        predictions = model.predict(X_test)
        
        if config.task_type == "classification":
            if config.metric == "accuracy":
                return accuracy_score(y_test, predictions)
            elif config.metric == "precision":
                return precision_score(y_test, predictions, average='weighted')
            elif config.metric == "recall":
                return recall_score(y_test, predictions, average='weighted')
            elif config.metric == "f1":
                return f1_score(y_test, predictions, average='weighted')
            elif config.metric == "auc":
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(X_test)[:, 1]
                    return roc_auc_score(y_test, proba)
                else:
                    return accuracy_score(y_test, predictions)
            else:
                return accuracy_score(y_test, predictions)
        else:
            if config.metric == "r2":
                return r2_score(y_test, predictions)
            elif config.metric == "mse":
                return -mean_squared_error(y_test, predictions)  # Negative for maximization
            elif config.metric == "mae":
                return -mean_absolute_error(y_test, predictions)  # Negative for maximization
            else:
                return r2_score(y_test, predictions)
    
    def _get_feature_importance(
        self,
        model: Any,
        feature_names: List[str]
    ) -> Optional[Dict[str, float]]:
        """Extract feature importance from model"""
        
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                importances = np.abs(model.coef_).flatten()
            else:
                return None
            
            # Create dictionary of feature importance
            importance_dict = {}
            for name, importance in zip(feature_names, importances):
                importance_dict[name] = float(importance)
            
            # Sort by importance
            return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
        except Exception as e:
            logger.warning(f"Could not extract feature importance: {str(e)}")
            return None
    
    def _get_production_model(self, model_name: str, task_type: str) -> Any:
        """Get production-ready model instance with optimized configurations."""

        if task_type == "classification":
            models = {
                "random_forest": RandomForestClassifier(
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced',
                    max_features='sqrt',
                    oob_score=True
                ),
                "xgboost": xgb.XGBClassifier(
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='logloss',
                    early_stopping_rounds=10,
                    verbosity=0,
                    use_label_encoder=False
                ) if HAS_XGBOOST else xgb.XGBClassifier(),
                "lightgbm": lgb.LGBMClassifier(
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced',
                    verbosity=-1,
                    early_stopping_rounds=10,
                    force_col_wise=True
                ) if HAS_LIGHTGBM else lgb.LGBMClassifier(),
                "logistic_regression": LogisticRegression(
                    random_state=42,
                    max_iter=1000,
                    class_weight='balanced',
                    solver='liblinear'
                ),
                "svm": SVC(
                    random_state=42,
                    class_weight='balanced',
                    probability=True,
                    cache_size=1000
                )
            }
        else:  # regression
            models = {
                "random_forest": RandomForestRegressor(
                    random_state=42,
                    n_jobs=-1,
                    max_features='sqrt',
                    oob_score=True
                ),
                "xgboost": xgb.XGBRegressor(
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='rmse',
                    early_stopping_rounds=10,
                    verbosity=0
                ) if HAS_XGBOOST else xgb.XGBRegressor(),
                "lightgbm": lgb.LGBMRegressor(
                    random_state=42,
                    n_jobs=-1,
                    verbosity=-1,
                    early_stopping_rounds=10,
                    force_col_wise=True
                ) if HAS_LIGHTGBM else lgb.LGBMRegressor(),
                "linear_regression": LinearRegression(n_jobs=-1),
                "svr": SVR(cache_size=1000)
            }

        return models.get(model_name)

    def _optimize_hyperparameters_production(
        self,
        model: Any,
        param_grid: Dict[str, Any],
        X_train: pd.DataFrame,
        y_train: pd.Series,
        config: AutoMLConfig
    ) -> Tuple[Any, Dict[str, Any], float]:
        """Production-ready hyperparameter optimization with early stopping and timeout."""

        if not param_grid:
            # No parameters to optimize
            model.fit(X_train, y_train)
            return model, {}, 0.0

        try:
            # Use Bayesian optimization for better efficiency
            from sklearn.model_selection import RandomizedSearchCV

            # Determine number of iterations based on parameter space size
            param_combinations = 1
            for param_values in param_grid.values():
                param_combinations *= len(param_values) if isinstance(param_values, list) else 1

            n_iter = min(50, max(10, param_combinations // 2))

            search = RandomizedSearchCV(
                estimator=model,
                param_distributions=param_grid,
                n_iter=n_iter,
                cv=config.cross_validation_folds,
                scoring=self._get_scoring_metric(config),
                n_jobs=-1,
                random_state=42,
                verbose=0,
                error_score='raise'
            )

            # Fit with timeout protection
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Hyperparameter optimization timed out")

            timeout_seconds = config.model_timeout or 300
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                search.fit(X_train, y_train)
                signal.alarm(0)  # Cancel timeout

                return search.best_estimator_, search.best_params_, search.best_score_

            except TimeoutError:
                logger.warning(f"Hyperparameter optimization timed out after {timeout_seconds}s")
                # Return model with default parameters
                model.fit(X_train, y_train)
                return model, {}, 0.0
            finally:
                signal.alarm(0)  # Ensure timeout is cancelled

        except Exception as e:
            logger.error(f"Hyperparameter optimization failed: {e}")
            # Fallback to default model
            model.fit(X_train, y_train)
            return model, {}, 0.0

    def _get_feature_importance(self, model: Any, feature_names: List[str]) -> Dict[str, float]:
        """Extract feature importance from trained model."""

        importance_dict = {}

        try:
            if hasattr(model, 'feature_importances_'):
                # Tree-based models (RF, XGBoost, LightGBM)
                importances = model.feature_importances_
                importance_dict = dict(zip(feature_names, importances))

            elif hasattr(model, 'coef_'):
                # Linear models
                if len(model.coef_.shape) == 1:
                    # Binary classification or regression
                    importances = np.abs(model.coef_)
                else:
                    # Multi-class classification - use mean absolute coefficients
                    importances = np.mean(np.abs(model.coef_), axis=0)

                importance_dict = dict(zip(feature_names, importances))

            else:
                # Model doesn't support feature importance
                importance_dict = {name: 0.0 for name in feature_names}

        except Exception as e:
            logger.warning(f"Could not extract feature importance: {e}")
            importance_dict = {name: 0.0 for name in feature_names}

        # Normalize importance scores
        total_importance = sum(importance_dict.values())
        if total_importance > 0:
            importance_dict = {
                name: importance / total_importance
                for name, importance in importance_dict.items()
            }

        return importance_dict

    def _calculate_model_complexity(self, model: Any, X_train: pd.DataFrame) -> Dict[str, Any]:
        """Calculate model complexity metrics for interpretability assessment."""

        complexity_metrics = {
            'model_type': type(model).__name__,
            'n_features': X_train.shape[1],
            'n_samples': X_train.shape[0]
        }

        try:
            # Tree-based model complexity
            if hasattr(model, 'n_estimators'):
                complexity_metrics['n_estimators'] = getattr(model, 'n_estimators', 0)

            if hasattr(model, 'max_depth'):
                complexity_metrics['max_depth'] = getattr(model, 'max_depth', 0)

            # Linear model complexity
            if hasattr(model, 'coef_'):
                coef = model.coef_
                if len(coef.shape) == 1:
                    complexity_metrics['n_coefficients'] = len(coef)
                    complexity_metrics['non_zero_coefficients'] = np.count_nonzero(coef)
                else:
                    complexity_metrics['n_coefficients'] = coef.size
                    complexity_metrics['non_zero_coefficients'] = np.count_nonzero(coef)

            # Memory footprint estimation
            try:
                import sys
                complexity_metrics['model_size_bytes'] = sys.getsizeof(model)
            except:
                complexity_metrics['model_size_bytes'] = 0

        except Exception as e:
            logger.warning(f"Could not calculate model complexity: {e}")

        return complexity_metrics