"""
AstroGeo Data Preprocessing
=============================
Sklearn-based preprocessing pipeline for numeric and categorical features.

Author: Production Team
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)


class AstroGeoPreprocessor:
    """
    Preprocessing pipeline for AstroGeo datasets.

    Features:
    - Automatic numeric/categorical column detection
    - Median imputation for missing numeric values
    - StandardScaler normalization
    - LabelEncoder for categorical columns
    - Separate target column handling
    """

    def __init__(self):
        self.numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.target_encoder: Optional[LabelEncoder] = None
        self.numeric_columns: List[str] = []
        self.categorical_columns: List[str] = []
        self.feature_names: List[str] = []
        self._is_fitted = False

    def fit_transform(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Fit the preprocessor and transform the DataFrame.

        Args:
            df: Input DataFrame.
            target_col: Name of the target column (excluded from features).

        Returns:
            Tuple of (X_transformed, y) where y is None if no target_col.
        """
        df = df.copy()
        y = None

        # Extract target
        if target_col and target_col in df.columns:
            y_raw = df.pop(target_col)

            if y_raw.dtype == "object" or y_raw.dtype.name == "category":
                self.target_encoder = LabelEncoder()
                y = self.target_encoder.fit_transform(y_raw)
            else:
                y = y_raw.values.astype(np.float64)

        # Identify column types
        self.numeric_columns = df.select_dtypes(
            include=["int64", "int32", "float64", "float32"]
        ).columns.tolist()

        self.categorical_columns = df.select_dtypes(
            include=["object", "category", "bool"]
        ).columns.tolist()

        self.feature_names = self.numeric_columns + self.categorical_columns

        # Encode categoricals
        cat_arrays = []
        for col in self.categorical_columns:
            le = LabelEncoder()
            encoded = le.fit_transform(df[col].astype(str))
            cat_arrays.append(encoded.reshape(-1, 1))
            self.label_encoders[col] = le

        # Transform numerics
        if self.numeric_columns:
            X_numeric = self.numeric_pipeline.fit_transform(df[self.numeric_columns])
        else:
            X_numeric = np.empty((len(df), 0))

        # Combine
        parts = [X_numeric]
        if cat_arrays:
            parts.append(np.hstack(cat_arrays))

        X = np.hstack(parts) if parts else np.empty((len(df), 0))
        self._is_fitted = True

        logger.info(
            f"Preprocessor fitted: {len(self.numeric_columns)} numeric, "
            f"{len(self.categorical_columns)} categorical columns"
        )
        return X, y

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform a new DataFrame using the fitted preprocessor.

        Args:
            df: Input DataFrame (must have same columns as fit_transform).

        Returns:
            Transformed numpy array.
        """
        if not self._is_fitted:
            raise RuntimeError("Preprocessor not fitted. Call fit_transform() first.")

        df = df.copy()

        # Encode categoricals
        cat_arrays = []
        for col in self.categorical_columns:
            if col in df.columns and col in self.label_encoders:
                le = self.label_encoders[col]
                # Handle unseen labels gracefully
                col_values = df[col].astype(str)
                encoded = []
                for val in col_values:
                    if val in le.classes_:
                        encoded.append(le.transform([val])[0])
                    else:
                        encoded.append(-1)  # Unknown category
                cat_arrays.append(np.array(encoded).reshape(-1, 1))

        # Transform numerics
        if self.numeric_columns:
            available_cols = [c for c in self.numeric_columns if c in df.columns]
            X_numeric = self.numeric_pipeline.transform(df[available_cols])
        else:
            X_numeric = np.empty((len(df), 0))

        # Combine
        parts = [X_numeric]
        if cat_arrays:
            parts.append(np.hstack(cat_arrays))

        return np.hstack(parts) if parts else np.empty((len(df), 0))

    def get_feature_names(self) -> List[str]:
        """Return ordered list of feature names after transformation."""
        return list(self.feature_names)

    def inverse_transform_target(self, y: np.ndarray) -> np.ndarray:
        """Inverse transform encoded target values back to original labels."""
        if self.target_encoder is not None:
            return self.target_encoder.inverse_transform(y.astype(int))
        return y


__all__ = ["AstroGeoPreprocessor"]
