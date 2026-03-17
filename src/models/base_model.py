"""
AstroGeo Base Model
====================
Base wrapper for all AstroGeo sklearn models.
Provides unified fit/predict/save/load interface with SHAP explainability.

Author: Production Team
Version: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)


class AstroGeoModel:
    """
    Base wrapper for all AstroGeo sklearn models.

    Features:
    - Unified fit/predict interface
    - SHAP-based feature explainability
    - Joblib serialization
    - MLflow-compatible metadata
    """

    def __init__(self, model_name: str, model_type: str = "classification"):
        """
        Initialize AstroGeoModel.

        Args:
            model_name: Name of the model (e.g. 'asteroid_planner')
            model_type: 'classification' or 'regression'
        """
        self.model_name = model_name
        self.model_type = model_type
        self.model: Optional[BaseEstimator] = None
        self.shap_explainer = None
        self.feature_names: List[str] = []
        self.model_version = "1.0.0"
        self._metadata: Dict[str, Any] = {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> "AstroGeoModel":
        """
        Train the model and set up the SHAP explainer.

        Args:
            X: Training features (n_samples, n_features)
            y: Training labels/values
            feature_names: Optional list of feature names

        Returns:
            self for chaining
        """
        if self.model is None:
            raise ValueError("No model set. Assign a sklearn estimator to self.model first.")

        X = np.asarray(X)
        y = np.asarray(y)

        if feature_names:
            self.feature_names = list(feature_names)
        elif not self.feature_names:
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        # Train model
        self.model.fit(X, y)

        # Set up SHAP explainer
        try:
            import shap

            self.shap_explainer = shap.TreeExplainer(self.model)
            logger.info(f"SHAP TreeExplainer initialized for '{self.model_name}'")
        except Exception as e:
            logger.warning(f"SHAP explainer setup failed (will use fallback): {e}")
            self.shap_explainer = None

        self._metadata.update({
            "n_train_samples": int(X.shape[0]),
            "n_features": int(X.shape[1]),
            "feature_names": self.feature_names,
        })

        logger.info(f"Model '{self.model_name}' trained on {X.shape[0]} samples")
        return self

    def predict(self, X: Union[np.ndarray, list]) -> Dict[str, Any]:
        """
        Return prediction + confidence + SHAP values.

        Args:
            X: Feature array (n_samples, n_features) or single sample list

        Returns:
            Dict with keys: label, confidence, probabilities, shap_values
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded.")

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        result: Dict[str, Any] = {}

        if self.model_type == "classification":
            prediction = self.model.predict(X)
            result["label"] = str(prediction[0])

            if hasattr(self.model, "predict_proba"):
                probas = self.model.predict_proba(X)[0]
                classes = self.model.classes_
                result["confidence"] = float(np.max(probas))
                result["probabilities"] = {
                    str(cls): round(float(p), 4) for cls, p in zip(classes, probas)
                }
            else:
                result["confidence"] = 1.0
                result["probabilities"] = {}
        else:
            # Regression
            prediction = self.model.predict(X)
            result["label"] = round(float(prediction[0]), 4)
            result["confidence"] = 0.85  # Placeholder confidence for regression
            result["probabilities"] = {}

        # SHAP values
        shap_vals = self.get_shap_explanation(X)
        result["shap_values"] = shap_vals

        return result

    def save(self, path: str) -> None:
        """
        Save model with joblib (model + metadata).

        Args:
            path: Filepath to save to (e.g. 'models/production/model.joblib')
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        bundle = {
            "model": self.model,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "feature_names": self.feature_names,
            "metadata": self._metadata,
        }

        joblib.dump(bundle, save_path)
        logger.info(f"Model saved to {save_path}")

    @classmethod
    def load(cls, path: str) -> "AstroGeoModel":
        """
        Load model from path.

        Args:
            path: Filepath to load from

        Returns:
            AstroGeoModel instance with model loaded
        """
        save_path = Path(path)
        if not save_path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        data = joblib.load(save_path)

        # Handle both raw sklearn model and bundled format
        if isinstance(data, dict) and "model" in data:
            instance = cls(
                model_name=data.get("model_name", save_path.stem),
                model_type=data.get("model_type", "classification"),
            )
            instance.model = data["model"]
            instance.model_version = data.get("model_version", "1.0.0")
            instance.feature_names = data.get("feature_names", [])
            instance._metadata = data.get("metadata", {})
        else:
            # Raw sklearn model
            instance = cls(model_name=save_path.stem)
            instance.model = data
            # Infer feature count
            if hasattr(data, "n_features_in_"):
                instance.feature_names = [
                    f"feature_{i}" for i in range(data.n_features_in_)
                ]

        # Set up SHAP
        try:
            import shap

            instance.shap_explainer = shap.TreeExplainer(instance.model)
        except Exception:
            instance.shap_explainer = None

        logger.info(f"Model loaded from {path}")
        return instance

    def get_shap_explanation(self, X: np.ndarray) -> Dict[str, float]:
        """
        Return feature_name: shap_value dict for the first sample.

        Args:
            X: Feature array (n_samples, n_features)

        Returns:
            Dict mapping feature names to SHAP values
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if self.shap_explainer is not None:
            try:
                shap_values = self.shap_explainer.shap_values(X)

                # For binary classification, shap_values is a list of 2 arrays
                if isinstance(shap_values, list):
                    # Use class 1 (positive class) SHAP values
                    vals = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
                else:
                    vals = shap_values[0]

                names = self.feature_names or [
                    f"feature_{i}" for i in range(len(vals))
                ]
                return {
                    name: round(float(val), 4)
                    for name, val in zip(names, vals)
                }
            except Exception as e:
                logger.warning(f"SHAP explanation failed: {e}")

        # Fallback: use feature importances if available
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            names = self.feature_names or [
                f"feature_{i}" for i in range(len(importances))
            ]
            return {
                name: round(float(imp), 4)
                for name, imp in zip(names, importances)
            }

        return {}


__all__ = ["AstroGeoModel"]
