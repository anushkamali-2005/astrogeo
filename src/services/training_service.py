"""
Model Training Service
======================
End-to-end ML model training pipeline with MLflow tracking:
- Data loading and preprocessing
- Feature engineering
- Model training with cross-validation
- Hyperparameter tuning
- Model evaluation
- MLflow experiment tracking
- Model registration and versioning

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import (
    ModelTrainingError,
    DataValidationError,
    MLflowError
)


logger = get_logger(__name__)


# ============================================================================
# MLFLOW CONFIGURATION
# ============================================================================

# Initialize MLflow
mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
mlflow_client = MlflowClient()


# ============================================================================
# MODEL TRAINING SERVICE
# ============================================================================

class ModelTrainingService:
    """
    Service for end-to-end ML model training.
    
    Features:
    - Data loading and validation
    - Preprocessing and feature engineering
    - Model training with cross-validation
    - Hyperparameter optimization
    - MLflow experiment tracking
    - Model evaluation and metrics
    - Model registration
    
    Performance:
    - Time complexity: O(n*m*k) where n=samples, m=features, k=CV folds
    - Space complexity: O(n*m)
    """
    
    def __init__(self, experiment_name: str = "astrogeo_experiments"):
        """
        Initialize training service.
        
        Args:
            experiment_name: MLflow experiment name
        """
        self.experiment_name = experiment_name
        
        # Create or get experiment
        try:
            self.experiment_id = mlflow.create_experiment(experiment_name)
        except Exception:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            self.experiment_id = experiment.experiment_id if experiment else None
        
        logger.info(
            "Training service initialized",
            extra={"experiment": experiment_name, "experiment_id": self.experiment_id}
        )
    
    async def train_model(
        self,
        model_id: str,
        dataset_path: str,
        model_type: str,
        hyperparameters: Dict[str, Any],
        target_column: str = "target",
        test_size: float = 0.2,
        cv_folds: int = 5,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Train ML model with MLflow tracking.
        
        Args:
            model_id: Unique model identifier
            dataset_path: Path to training dataset
            model_type: Type of model (random_forest, gradient_boosting, etc.)
            hyperparameters: Model hyperparameters
            target_column: Target column name
            test_size: Test set size (0-1)
            cv_folds: Cross-validation folds
            random_state: Random seed
            
        Returns:
            dict: Training results with metrics
            
        Raises:
            ModelTrainingError: If training fails
            DataValidationError: If data is invalid
        """
        logger.info(
            "Starting model training",
            extra={
                "model_id": model_id,
                "model_type": model_type,
                "dataset": dataset_path
            }
        )
        
        try:
            # Start MLflow run
            with mlflow.start_run(experiment_id=self.experiment_id, run_name=model_id):
                # Log parameters
                mlflow.log_params({
                    "model_id": model_id,
                    "model_type": model_type,
                    "test_size": test_size,
                    "cv_folds": cv_folds,
                    "random_state": random_state,
                    **hyperparameters
                })
                
                # Load and validate data
                X, y = await self._load_data(dataset_path, target_column)
                
                # Log data stats
                mlflow.log_metrics({
                    "n_samples": len(X),
                    "n_features": X.shape[1],
                    "n_classes": len(np.unique(y))
                })
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state, stratify=y
                )
                
                # Create and train model
                model = self._create_model(model_type, hyperparameters)
                
                training_start = datetime.utcnow()
                model.fit(X_train, y_train)
                training_duration = (datetime.utcnow() - training_start).total_seconds()
                
                mlflow.log_metric("training_duration_seconds", training_duration)
                
                # Cross-validation
                cv_scores = cross_val_score(
                    model, X_train, y_train, cv=cv_folds, scoring="accuracy"
                )
                
                mlflow.log_metrics({
                    "cv_mean_accuracy": cv_scores.mean(),
                    "cv_std_accuracy": cv_scores.std()
                })
                
                # Evaluate on test set
                metrics = self._evaluate_model(model, X_test, y_test)
                mlflow.log_metrics(metrics)
                
                # Log model
                mlflow.sklearn.log_model(
                    model,
                    "model",
                    registered_model_name=f"astrogeo_{model_type}"
                )
                
                # Get run info
                run = mlflow.active_run()
                run_id = run.info.run_id
                
                logger.info(
                    "Model training completed",
                    extra={
                        "model_id": model_id,
                        "run_id": run_id,
                        "accuracy": metrics["test_accuracy"]
                    }
                )
                
                return {
                    "status": "success",
                    "model_id": model_id,
                    "run_id": run_id,
                    "model_type": model_type,
                    "metrics": metrics,
                    "cv_scores": {
                        "mean": float(cv_scores.mean()),
                        "std": float(cv_scores.std()),
                        "all_folds": cv_scores.tolist()
                    },
                    "training_duration_seconds": training_duration,
                    "n_samples_train": len(X_train),
                    "n_samples_test": len(X_test),
                    "completed_at": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error("Model training failed", error=e)
            raise ModelTrainingError(
                model_id=model_id,
                details={"error": str(e), "model_type": model_type}
            )
    
    async def _load_data(
        self,
        dataset_path: str,
        target_column: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load and validate dataset.
        
        Args:
            dataset_path: Path to dataset file
            target_column: Target column name
            
        Returns:
            tuple: (X, y) features and target
            
        Raises:
            DataValidationError: If data is invalid
        """
        try:
            # Load data (supports CSV, Parquet)
            if dataset_path.endswith('.csv'):
                df = pd.read_csv(dataset_path)
            elif dataset_path.endswith('.parquet'):
                df = pd.read_parquet(dataset_path)
            else:
                raise DataValidationError(
                    message="Unsupported file format",
                    details={"path": dataset_path}
                )
            
            # Validate
            if target_column not in df.columns:
                raise DataValidationError(
                    message="Target column not found",
                    details={"target": target_column, "columns": list(df.columns)}
                )
            
            if df.empty:
                raise DataValidationError(
                    message="Dataset is empty",
                    details={"path": dataset_path}
                )
            
            # Check for missing values
            missing_pct = (df.isnull().sum() / len(df) * 100).to_dict()
            if any(pct > 50 for pct in missing_pct.values()):
                logger.warning(
                    "High missing value percentage detected",
                    extra={"missing_pct": missing_pct}
                )
            
            # Split features and target
            X = df.drop(columns=[target_column]).values
            y = df[target_column].values
            
            logger.info(
                "Data loaded successfully",
                extra={
                    "n_samples": len(X),
                    "n_features": X.shape[1],
                    "target_classes": len(np.unique(y))
                }
            )
            
            return X, y
        
        except Exception as e:
            logger.error("Data loading failed", error=e)
            raise DataValidationError(
                message="Failed to load dataset",
                details={"path": dataset_path, "error": str(e)}
            )
    
    def _create_model(self, model_type: str, hyperparameters: Dict[str, Any]):
        """
        Create model instance based on type.
        
        Args:
            model_type: Model type
            hyperparameters: Model hyperparameters
            
        Returns:
            Model instance
        """
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import SVC
        
        models = {
            "random_forest": RandomForestClassifier,
            "gradient_boosting": GradientBoostingClassifier,
            "logistic_regression": LogisticRegression,
            "svm": SVC
        }
        
        if model_type not in models:
            raise ModelTrainingError(
                model_id="unknown",
                details={"error": f"Unknown model type: {model_type}"}
            )
        
        model_class = models[model_type]
        return model_class(**hyperparameters)
    
    def _evaluate_model(
        self,
        model,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            
        Returns:
            dict: Evaluation metrics
        """
        # Predictions
        y_pred = model.predict(X_test)
        
        # Probabilities (if available)
        try:
            y_proba = model.predict_proba(X_test)[:, 1]
            has_proba = True
        except Exception:
            y_proba = None
            has_proba = False
        
        # Calculate metrics
        metrics = {
            "test_accuracy": float(accuracy_score(y_test, y_pred)),
            "test_precision": float(precision_score(y_test, y_pred, average="weighted")),
            "test_recall": float(recall_score(y_test, y_pred, average="weighted")),
            "test_f1": float(f1_score(y_test, y_pred, average="weighted"))
        }
        
        # Add AUC if probabilities available
        if has_proba and len(np.unique(y_test)) == 2:
            metrics["test_auc_roc"] = float(roc_auc_score(y_test, y_proba))
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        metrics["confusion_matrix"] = cm.tolist()
        
        return metrics
    
    async def load_model(self, model_id: str, version: Optional[str] = None) -> Any:
        """
        Load trained model from MLflow.
        
        Args:
            model_id: Model identifier
            version: Model version (None for latest)
            
        Returns:
            Loaded model
        """
        try:
            if version:
                model_uri = f"models:/{model_id}/{version}"
            else:
                model_uri = f"models:/{model_id}/latest"
            
            model = mlflow.sklearn.load_model(model_uri)
            
            logger.info(
                "Model loaded",
                extra={"model_id": model_id, "version": version}
            )
            
            return model
        
        except Exception as e:
            logger.error("Model loading failed", error=e)
            raise MLflowError(
                message="Failed to load model",
                details={"model_id": model_id, "version": version, "error": str(e)}
            )
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get model metadata and metrics.
        
        Args:
            model_id: Model identifier
            
        Returns:
            dict: Model information
        """
        try:
            model_versions = mlflow_client.search_model_versions(f"name='{model_id}'")
            
            if not model_versions:
                return {"status": "not_found", "model_id": model_id}
            
            latest_version = model_versions[0]
            
            # Get run details
            run = mlflow_client.get_run(latest_version.run_id)
            
            return {
                "status": "found",
                "model_id": model_id,
                "version": latest_version.version,
                "run_id": latest_version.run_id,
                "metrics": run.data.metrics,
                "parameters": run.data.params,
                "created_at": datetime.fromtimestamp(latest_version.creation_timestamp / 1000).isoformat()
            }
        
        except Exception as e:
            logger.error("Failed to get model info", error=e)
            raise MLflowError(
                message="Failed to get model info",
                details={"model_id": model_id, "error": str(e)}
            )


# Export
__all__ = ["ModelTrainingService"]
