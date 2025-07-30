"""
Unit tests for advanced ML components.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core_infra.services.advanced_ml.deep_learning_engine import (
    DeepLearningEngine,
    ArchitectureType
)
from core_infra.services.advanced_ml.automl_pipeline import (
    AutoMLPipeline,
    AutoMLConfig
)


class TestDeepLearningEngine:
    """Test deep learning engine with production implementations."""
    
    @pytest.fixture
    def dl_engine(self):
        """Create deep learning engine for testing."""
        mock_supabase = Mock()
        return DeepLearningEngine(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_build_tensorflow_feedforward_model(self, dl_engine):
        """Test building TensorFlow feedforward model."""
        input_shape = (10,)
        model_config = {
            'hidden_layers': [64, 32],
            'dropout_rate': 0.3,
            'activation': 'relu',
            'output_units': 1,
            'output_activation': 'sigmoid',
            'use_batch_norm': True,
            'l2_regularization': 0.001
        }
        
        with patch('core_infra.services.advanced_ml.deep_learning_engine.HAS_DL_LIBRARIES', True):
            with patch('tensorflow.keras.Sequential') as mock_sequential:
                mock_model = Mock()
                mock_sequential.return_value = mock_model
                
                model = await dl_engine.build_model(
                    input_shape=input_shape,
                    model_type="classification",
                    model_config=model_config,
                    framework="tensorflow"
                )
                
                assert model is not None
                mock_sequential.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_pytorch_feedforward_model(self, dl_engine):
        """Test building PyTorch feedforward model."""
        input_shape = (10,)
        model_config = {
            'hidden_layers': [64, 32],
            'dropout_rate': 0.3,
            'output_units': 1,
            'output_activation': 'sigmoid',
            'use_batch_norm': True
        }
        
        with patch('core_infra.services.advanced_ml.deep_learning_engine.HAS_DL_LIBRARIES', True):
            with patch('torch.nn.Module') as mock_module:
                model = await dl_engine.build_model(
                    input_shape=input_shape,
                    model_type="classification",
                    model_config=model_config,
                    framework="pytorch"
                )
                
                assert model is not None
    
    @pytest.mark.asyncio
    async def test_build_cnn_model(self, dl_engine):
        """Test building CNN model."""
        input_shape = (32, 32, 3)
        model_config = {
            'conv_layers': [
                {'filters': 32, 'kernel_size': 3},
                {'filters': 64, 'kernel_size': 3}
            ],
            'dense_layers': [128, 64],
            'dropout_rate': 0.25,
            'output_units': 10,
            'output_activation': 'softmax'
        }
        
        with patch('core_infra.services.advanced_ml.deep_learning_engine.HAS_DL_LIBRARIES', True):
            with patch('tensorflow.keras.Sequential') as mock_sequential:
                mock_model = Mock()
                mock_sequential.return_value = mock_model
                
                model = await dl_engine.build_model(
                    input_shape=input_shape,
                    model_type="classification",
                    model_config=model_config,
                    framework="tensorflow"
                )
                
                assert model is not None
    
    @pytest.mark.asyncio
    async def test_train_model_tensorflow(self, dl_engine):
        """Test training TensorFlow model."""
        mock_model = Mock()
        mock_model.fit.return_value = Mock(history={'loss': [0.5, 0.3], 'accuracy': [0.8, 0.9]})
        mock_model.evaluate.return_value = [0.25, 0.92]
        
        X_train = np.random.random((100, 10))
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.random((20, 10))
        y_val = np.random.randint(0, 2, 20)
        
        training_config = {
            'epochs': 10,
            'batch_size': 32,
            'learning_rate': 0.001,
            'early_stopping': True,
            'patience': 5
        }
        
        with patch('core_infra.services.advanced_ml.deep_learning_engine.HAS_DL_LIBRARIES', True):
            result = await dl_engine.train_model(
                model=mock_model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                training_config=training_config,
                framework="tensorflow"
            )
            
            assert result['status'] == 'success'
            assert 'training_history' in result
            assert 'final_metrics' in result
            mock_model.fit.assert_called_once()


class TestAutoMLPipeline:
    """Test AutoML pipeline with production implementations."""
    
    @pytest.fixture
    def automl_pipeline(self):
        """Create AutoML pipeline for testing."""
        mock_supabase = Mock()
        return AutoMLPipeline(mock_supabase)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        np.random.seed(42)
        data = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.normal(0, 1, 1000),
            'feature3': np.random.randint(0, 5, 1000),
            'feature4': np.random.random(1000),
            'target': np.random.randint(0, 2, 1000)
        })
        return data
    
    def test_get_production_model(self, automl_pipeline):
        """Test getting production-ready models."""
        # Test classification models
        rf_model = automl_pipeline._get_production_model('random_forest', 'classification')
        assert rf_model is not None
        assert hasattr(rf_model, 'fit')
        assert hasattr(rf_model, 'predict')
        
        # Test regression models
        rf_reg_model = automl_pipeline._get_production_model('random_forest', 'regression')
        assert rf_reg_model is not None
        assert hasattr(rf_reg_model, 'fit')
        assert hasattr(rf_reg_model, 'predict')
    
    def test_get_production_param_grid(self, automl_pipeline):
        """Test getting production parameter grids."""
        # Test random forest parameters
        rf_params = automl_pipeline._get_production_param_grid('random_forest')
        assert isinstance(rf_params, dict)
        assert 'n_estimators' in rf_params
        assert 'max_depth' in rf_params
        
        # Test XGBoost parameters
        xgb_params = automl_pipeline._get_production_param_grid('xgboost')
        assert isinstance(xgb_params, dict)
        assert 'n_estimators' in xgb_params
        assert 'learning_rate' in xgb_params
    
    def test_calculate_production_metrics_classification(self, automl_pipeline):
        """Test calculating comprehensive classification metrics."""
        y_true = np.array([0, 1, 1, 0, 1, 0, 1, 1, 0, 0])
        y_pred = np.array([0, 1, 0, 0, 1, 1, 1, 1, 0, 0])
        y_pred_proba = np.array([
            [0.8, 0.2], [0.3, 0.7], [0.6, 0.4], [0.9, 0.1], [0.2, 0.8],
            [0.4, 0.6], [0.1, 0.9], [0.2, 0.8], [0.7, 0.3], [0.8, 0.2]
        ])
        
        metrics = automl_pipeline._calculate_production_metrics(
            y_true, y_pred, y_pred_proba, 'classification'
        )
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'roc_auc' in metrics
        assert 'log_loss' in metrics
        
        # Check metric values are reasonable
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['roc_auc'] <= 1
    
    def test_calculate_production_metrics_regression(self, automl_pipeline):
        """Test calculating comprehensive regression metrics."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
        
        metrics = automl_pipeline._calculate_production_metrics(
            y_true, y_pred, None, 'regression'
        )
        
        assert 'r2_score' in metrics
        assert 'mean_absolute_error' in metrics
        assert 'mean_squared_error' in metrics
        assert 'root_mean_squared_error' in metrics
        assert 'explained_variance_score' in metrics
        
        # Check metric values are reasonable
        assert metrics['r2_score'] <= 1
        assert metrics['mean_absolute_error'] >= 0
        assert metrics['mean_squared_error'] >= 0
    
    def test_get_feature_importance(self, automl_pipeline):
        """Test extracting feature importance from models."""
        # Mock tree-based model with feature_importances_
        mock_model = Mock()
        mock_model.feature_importances_ = np.array([0.3, 0.5, 0.2])
        feature_names = ['feature1', 'feature2', 'feature3']
        
        importance = automl_pipeline._get_feature_importance(mock_model, feature_names)
        
        assert isinstance(importance, dict)
        assert len(importance) == 3
        assert all(name in importance for name in feature_names)
        assert abs(sum(importance.values()) - 1.0) < 1e-6  # Should be normalized
    
    def test_calculate_model_complexity(self, automl_pipeline):
        """Test calculating model complexity metrics."""
        # Mock model with complexity attributes
        mock_model = Mock()
        mock_model.n_estimators = 100
        mock_model.max_depth = 10
        
        X_train = pd.DataFrame(np.random.random((100, 5)))
        
        complexity = automl_pipeline._calculate_model_complexity(mock_model, X_train)
        
        assert isinstance(complexity, dict)
        assert 'model_type' in complexity
        assert 'n_features' in complexity
        assert 'n_samples' in complexity
        assert complexity['n_features'] == 5
        assert complexity['n_samples'] == 100
    
    @pytest.mark.asyncio
    async def test_run_automl_mock_libraries(self, automl_pipeline, sample_data):
        """Test AutoML pipeline with mock libraries."""
        config = {
            'models': ['random_forest', 'logistic_regression'],
            'metric': 'accuracy',
            'cross_validation_folds': 3,
            'test_size': 0.2,
            'feature_engineering': True,
            'hyperparameter_optimization': True
        }
        
        with patch('core_infra.services.advanced_ml.automl_pipeline.HAS_AUTOML_LIBRARIES', False):
            result = await automl_pipeline.run_automl(
                data=sample_data,
                target_column='target',
                model_type='classification',
                automl_config=config
            )
            
            assert result['status'] == 'success'
            assert 'best_model' in result
            assert 'model_results' in result
            assert 'total_time' in result
    
    def test_optimize_hyperparameters_production(self, automl_pipeline):
        """Test production hyperparameter optimization."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.datasets import make_classification
        
        # Create sample data
        X, y = make_classification(n_samples=100, n_features=10, random_state=42)
        X_df = pd.DataFrame(X)
        y_series = pd.Series(y)
        
        model = RandomForestClassifier(random_state=42)
        param_grid = {
            'n_estimators': [10, 20],
            'max_depth': [3, 5]
        }
        
        config = AutoMLConfig(
            task_type='classification',
            cross_validation_folds=3,
            model_timeout=60
        )
        
        best_model, best_params, best_score = automl_pipeline._optimize_hyperparameters_production(
            model, param_grid, X_df, y_series, config
        )
        
        assert best_model is not None
        assert isinstance(best_params, dict)
        assert isinstance(best_score, (int, float))
