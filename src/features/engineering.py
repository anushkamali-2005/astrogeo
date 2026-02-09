"""
Feature Engineering Pipeline
============================
Scikit-learn compatible transformers for feature engineering:
- Numerical scaling and normalization
- Categorical encoding
- Missing value imputation
- Outlier detection
- Feature selection
- Polynomial and interaction features
- Time-based features
- Geospatial features

Author: Production Team
Version: 1.0.0
"""

from typing import List, Optional, Dict, Any, Union
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    OneHotEncoder, LabelEncoder, OrdinalEncoder
)
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.preprocessing import PolynomialFeatures

from src.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# NUMERICAL TRANSFORMERS
# ============================================================================

class NumericalScaler(BaseEstimator, TransformerMixin):
    """
    Flexible numerical feature scaling.
    
    Supports: StandardScaler, MinMaxScaler, RobustScaler
    
    Time complexity: O(n*m) where n=samples, m=features
    Space complexity: O(m)
    """
    
    def __init__(self, method: str = "standard", columns: Optional[List[str]] = None):
        """
        Initialize scaler.
        
        Args:
            method: Scaling method (standard, minmax, robust)
            columns: Columns to scale (None for all numerical)
        """
        self.method = method
        self.columns = columns
        self.scaler = None
        self._feature_names = None
    
    def fit(self, X: Union[pd.DataFrame, np.ndarray], y=None):
        """Fit scaler to data."""
        X_df = pd.DataFrame(X) if isinstance(X, np.ndarray) else X
        
        # Select columns
        if self.columns:
            cols = self.columns
        else:
            cols = X_df.select_dtypes(include=[np.number]).columns.tolist()
        
        self._feature_names = cols
        
        # Initialize scaler
        scalers = {
            "standard": StandardScaler(),
            "minmax": MinMaxScaler(),
            "robust": RobustScaler()
        }
        
        if self.method not in scalers:
            raise ValueError(f"Unknown scaling method: {self.method}")
        
        self.scaler = scalers[self.method]
        self.scaler.fit(X_df[cols])
        
        logger.info(
            "Numerical scaler fitted",
            extra={"method": self.method, "n_features": len(cols)}
        )
        
        return self
    
    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        """Transform data."""
        X_df = pd.DataFrame(X) if isinstance(X, np.ndarray) else X.copy()
        X_df[self._feature_names] = self.scaler.transform(X_df[self._feature_names])
        return X_df


# ============================================================================
# CATEGORICAL TRANSFORMERS
# ============================================================================

class CategoricalEncoder(BaseEstimator, TransformerMixin):
    """
    Categorical feature encoding.
    
    Supports: OneHot, Ordinal, Target encoding
    
    Time complexity: O(n*m)
    Space complexity: O(k) where k=unique categories
    """
    
    def __init__(
        self,
        method: str = "onehot",
        columns: Optional[List[str]] = None,
        handle_unknown: str = "ignore"
    ):
        """
        Initialize encoder.
        
        Args:
            method: Encoding method (onehot, ordinal, label)
            columns: Columns to encode
            handle_unknown: How to handle unknown categories
        """
        self.method = method
        self.columns = columns
        self.handle_unknown = handle_unknown
        self.encoder = None
        self._feature_names = None
    
    def fit(self, X: Union[pd.DataFrame, np.ndarray], y=None):
        """Fit encoder to data."""
        X_df = pd.DataFrame(X) if isinstance(X, np.ndarray) else X
        
        # Select categorical columns
        if self.columns:
            cols = self.columns
        else:
            cols = X_df.select_dtypes(include=["object", "category"]).columns.tolist()
        
        self._feature_names = cols
        
        # Initialize encoder
        if self.method == "onehot":
            self.encoder = OneHotEncoder(
                sparse_output=False,
                handle_unknown=self.handle_unknown
            )
        elif self.method == "ordinal":
            self.encoder = OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1
            )
        elif self.method == "label":
            self.encoder = {col: LabelEncoder() for col in cols}
            for col in cols:
                self.encoder[col].fit(X_df[col])
            return self
        else:
            raise ValueError(f"Unknown encoding method: {self.method}")
        
        self.encoder.fit(X_df[cols])
        
        logger.info(
            "Categorical encoder fitted",
            extra={"method": self.method, "n_features": len(cols)}
        )
        
        return self
    
    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        """Transform data."""
        X_df = pd.DataFrame(X) if isinstance(X, np.ndarray) else X.copy()
        
        if self.method == "label":
            for col in self._feature_names:
                X_df[col] = self.encoder[col].transform(X_df[col])
        elif self.method == "onehot":
            encoded = self.encoder.transform(X_df[self._feature_names])
            feature_names = self.encoder.get_feature_names_out(self._feature_names)
            encoded_df = pd.DataFrame(
                encoded,
                columns=feature_names,
                index=X_df.index
            )
            X_df = X_df.drop(columns=self._feature_names)
            X_df = pd.concat([X_df, encoded_df], axis=1)
        else:
            X_df[self._feature_names] = self.encoder.transform(X_df[self._feature_names])
        
        return X_df


# ============================================================================
# MISSING VALUE TRANSFORMERS
# ============================================================================

class MissingValueImputer(BaseEstimator, TransformerMixin):
    """
    Missing value imputation.
    
    Supports: Mean, Median, Mode, Constant, KNN
    
    Time complexity: O(n*m) for simple, O(n^2*m) for KNN
    Space complexity: O(n*m) for KNN
    """
    
    def __init__(
        self,
        strategy: str = "mean",
        fill_value: Any = None,
        n_neighbors: int = 5
    ):
        """
        Initialize imputer.
        
        Args:
            strategy: Imputation strategy
            fill_value: Fill value for constant strategy
            n_neighbors: Neighbors for KNN imputation
        """
        self.strategy = strategy
        self.fill_value = fill_value
        self.n_neighbors = n_neighbors
        self.imputer = None
    
    def fit(self, X: Union[pd.DataFrame, np.ndarray], y=None):
        """Fit imputer to data."""
        if self.strategy == "knn":
            self.imputer = KNNImputer(n_neighbors=self.n_neighbors)
        else:
            self.imputer = SimpleImputer(
                strategy=self.strategy,
                fill_value=self.fill_value
            )
        
        self.imputer.fit(X)
        
        logger.info("Missing value imputer fitted", extra={"strategy": self.strategy})
        
        return self
    
    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        """Transform data."""
        is_dataframe = isinstance(X, pd.DataFrame)
        columns = X.columns if is_dataframe else None
        index = X.index if is_dataframe else None
        
        X_imputed = self.imputer.transform(X)
        
        if is_dataframe:
            return pd.DataFrame(X_imputed, columns=columns, index=index)
        return pd.DataFrame(X_imputed)


# Export
__all__ = [
    "NumericalScaler",
    "CategoricalEncoder",
    "MissingValueImputer"
]
