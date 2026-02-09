"""
Data Transformers
==================
Production-level data transformation pipeline using decorator pattern.

Transformers:
- Normalization (scaling, standardization)
- Encoding (categorical, ordinal, one-hot)
- Feature engineering (aggregation, binning)
- Missing value imputation

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder

from src.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# BASE TRANSFORMER
# ============================================================================

class DataTransformer(ABC):
    """
    Abstract base transformer with pipeline pattern.
    
    Design Pattern: Decorator/Pipeline
    """
    
    def __init__(self, next_transformer: Optional['DataTransformer'] = None):
        """
        Initialize transformer.
        
        Args:
            next_transformer: Next transformer in pipeline
        """
        self.next_transformer = next_transformer
        self.fitted = False
    
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data and chain to next transformer.
        
        Args:
            data: DataFrame to transform
            
        Returns:
            DataFrame: Transformed data
        """
        # Apply this transformation
        transformed = self._transform_impl(data.copy())
        
        # Chain to next transformer
        if self.next_transformer:
            transformed = self.next_transformer.transform(transformed)
        
        return transformed
    
    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Fit transformer and transform data.
        
        Args:
            data: DataFrame to fit and transform
            
        Returns:
            DataFrame: Transformed data
        """
        # Fit this transformer
        self._fit_impl(data)
        self.fitted = True
        
        # Transform with this transformer
        transformed = self._transform_impl(data.copy())
        
        # Chain to next transformer
        if self.next_transformer:
            transformed = self.next_transformer.fit_transform(transformed)
        
        return transformed
    
    @abstractmethod
    def _fit_impl(self, data: pd.DataFrame) -> None:
        """
        Fit transformer to data.
        
        Args:
            data: DataFrame to fit
        """
        pass
    
    @abstractmethod
    def _transform_impl(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data.
        
        Args:
            data: DataFrame to transform
            
        Returns:
            DataFrame: Transformed data
        """
        pass


# ============================================================================
# NORMALIZATION TRANSFORMER
# ============================================================================

class NormalizationTransformer(DataTransformer):
    """
    Normalizes numeric columns using various strategies.
    """
    
    class Strategy(str, Enum):
        """Normalization strategies."""
        STANDARD = "standard"  # Z-score normalization
        MINMAX = "minmax"      # Min-max scaling to [0, 1]
        ROBUST = "robust"      # Robust scaling using median and IQR
    
    def __init__(
        self,
        columns: Optional[List[str]] = None,
        strategy: Strategy = Strategy.STANDARD,
        next_transformer: Optional[DataTransformer] = None
    ):
        """
        Initialize normalization transformer.
        
        Args:
            columns: Columns to normalize (None = all numeric)
            strategy: Normalization strategy
            next_transformer: Next transformer in pipeline
        """
        super().__init__(next_transformer)
        self.columns = columns
        self.strategy = strategy
        self.scalers: Dict[str, Any] = {}
    
    def _fit_impl(self, data: pd.DataFrame) -> None:
        """Fit scalers to data."""
        columns_to_normalize = self.columns or data.select_dtypes(include=[np.number]).columns
        
        for col in columns_to_normalize:
            if col not in data.columns:
                continue
            
            if self.strategy == self.Strategy.STANDARD:
                scaler = StandardScaler()
            elif self.strategy == self.Strategy.MINMAX:
                scaler = MinMaxScaler()
            else:  # ROBUST
                from sklearn.preprocessing import RobustScaler
                scaler = RobustScaler()
            
            scaler.fit(data[[col]])
            self.scalers[col] = scaler
        
        logger.debug(f"Fitted normalization for {len(self.scalers)} columns")
    
    def _transform_impl(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize columns."""
        for col, scaler in self.scalers.items():
            if col in data.columns:
                data[col] = scaler.transform(data[[col]])
        
        logger.debug(f"Normalized {len(self.scalers)} columns")
        return data


# ============================================================================
# ENCODING TRANSFORMER
# ============================================================================

class EncodingTransformer(DataTransformer):
    """
    Encodes categorical columns using various strategies.
    """
    
    class Strategy(str, Enum):
        """Encoding strategies."""
        LABEL = "label"          # Label encoding (0, 1, 2, ...)
        ONEHOT = "onehot"        # One-hot encoding
        TARGET = "target"        # Target encoding (mean of target)
    
    def __init__(
        self,
        columns: Optional[List[str]] = None,
        strategy: Strategy = Strategy.LABEL,
        next_transformer: Optional[DataTransformer] = None
    ):
        """
        Initialize encoding transformer.
        
        Args:
            columns: Columns to encode (None = all categorical)
            strategy: Encoding strategy
            next_transformer: Next transformer in pipeline
        """
        super().__init__(next_transformer)
        self.columns = columns
        self.strategy = strategy
        self.encoders: Dict[str, Any] = {}
    
    def _fit_impl(self, data: pd.DataFrame) -> None:
        """Fit encoders to data."""
        columns_to_encode = self.columns or data.select_dtypes(include=['object', 'category']).columns
        
        for col in columns_to_encode:
            if col not in data.columns:
                continue
            
            if self.strategy == self.Strategy.LABEL:
                encoder = LabelEncoder()
                encoder.fit(data[col].astype(str))
                self.encoders[col] = encoder
            
            # One-hot and target encoding handled differently
        
        logger.debug(f"Fitted encoding for {len(self.encoders)} columns")
    
    def _transform_impl(self, data: pd.DataFrame) -> pd.DataFrame:
        """Encode columns."""
        if self.strategy == self.Strategy.LABEL:
            for col, encoder in self.encoders.items():
                if col in data.columns:
                    data[col] = encoder.transform(data[col].astype(str))
        
        elif self.strategy == self.Strategy.ONEHOT:
            columns_to_encode = self.columns or data.select_dtypes(include=['object', 'category']).columns
            data = pd.get_dummies(data, columns=list(columns_to_encode), prefix=list(columns_to_encode))
        
        logger.debug(f"Encoded {len(self.encoders)} columns")
        return data


# ============================================================================
# FEATURE ENGINEERING TRANSFORMER
# ============================================================================

class FeatureEngineeringTransformer(DataTransformer):
    """
    Creates new features through engineering.
    """
    
    def __init__(
        self,
        feature_functions: Optional[Dict[str, Callable]] = None,
        next_transformer: Optional[DataTransformer] = None
    ):
        """
        Initialize feature engineering transformer.
        
        Args:
            feature_functions: Dict of {new_column_name: function(df) -> Series}
            next_transformer: Next transformer in pipeline
        """
        super().__init__(next_transformer)
        self.feature_functions = feature_functions or {}
    
    def _fit_impl(self, data: pd.DataFrame) -> None:
        """No fitting needed for feature engineering."""
        pass
    
    def _transform_impl(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create new features."""
        for feature_name, func in self.feature_functions.items():
            try:
                data[feature_name] = func(data)
                logger.debug(f"Created feature: {feature_name}")
            except Exception as e:
                logger.warning(f"Failed to create feature {feature_name}", error=e)
        
        return data


# ============================================================================
# MISSING VALUE IMPUTATION TRANSFORMER
# ============================================================================

class ImputationTransformer(DataTransformer):
    """
    Imputes missing values using various strategies.
    """
    
    class Strategy(str, Enum):
        """Imputation strategies."""
        MEAN = "mean"
        MEDIAN = "median"
        MODE = "mode"
        CONSTANT = "constant"
        FORWARD_FILL = "ffill"
        BACKWARD_FILL = "bfill"
    
    def __init__(
        self,
        strategy: Strategy = Strategy.MEAN,
        fill_value: Any = None,
        columns: Optional[List[str]] = None,
        next_transformer: Optional[DataTransformer] = None
    ):
        """
        Initialize imputation transformer.
        
        Args:
            strategy: Imputation strategy
            fill_value: Value to use for CONSTANT strategy
            columns: Columns to impute (None = all with missing)
            next_transformer: Next transformer in pipeline
        """
        super().__init__(next_transformer)
        self.strategy = strategy
        self.fill_value = fill_value
        self.columns = columns
        self.fill_values: Dict[str, Any] = {}
    
    def _fit_impl(self, data: pd.DataFrame) -> None:
        """Fit imputation values."""
        columns_to_impute = self.columns or data.columns[data.isna().any()].tolist()
        
        for col in columns_to_impute:
            if col not in data.columns:
                continue
            
            if self.strategy == self.Strategy.MEAN:
                self.fill_values[col] = data[col].mean()
            elif self.strategy == self.Strategy.MEDIAN:
                self.fill_values[col] = data[col].median()
            elif self.strategy == self.Strategy.MODE:
                self.fill_values[col] = data[col].mode()[0] if not data[col].mode().empty else None
            elif self.strategy == self.Strategy.CONSTANT:
                self.fill_values[col] = self.fill_value
        
        logger.debug(f"Fitted imputation for {len(self.fill_values)} columns")
    
    def _transform_impl(self, data: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values."""
        if self.strategy in [self.Strategy.FORWARD_FILL, self.Strategy.BACKWARD_FILL]:
            method = 'ffill' if self.strategy == self.Strategy.FORWARD_FILL else 'bfill'
            data = data.fillna(method=method)
        else:
            for col, fill_val in self.fill_values.items():
                if col in data.columns:
                    data[col].fillna(fill_val, inplace=True)
        
        logger.debug(f"Imputed missing values in {len(self.fill_values)} columns")
        return data


# ============================================================================
# TRANSFORMATION PIPELINE
# ============================================================================

class TransformationPipeline:
    """
    Fluent builder for transformation pipeline.
    
    Design Pattern: Builder
    """
    
    def __init__(self):
        """Initialize transformation pipeline."""
        self.transformers: List[DataTransformer] = []
    
    def add_normalization(
        self,
        columns: Optional[List[str]] = None,
        strategy: NormalizationTransformer.Strategy = NormalizationTransformer.Strategy.STANDARD
    ) -> 'TransformationPipeline':
        """Add normalization step."""
        self.transformers.append(
            NormalizationTransformer(columns, strategy)
        )
        return self
    
    def add_encoding(
        self,
        columns: Optional[List[str]] = None,
        strategy: EncodingTransformer.Strategy = EncodingTransformer.Strategy.LABEL
    ) -> 'TransformationPipeline':
        """Add encoding step."""
        self.transformers.append(
            EncodingTransformer(columns, strategy)
        )
        return self
    
    def add_imputation(
        self,
        strategy: ImputationTransformer.Strategy = ImputationTransformer.Strategy.MEAN,
        fill_value: Any = None,
        columns: Optional[List[str]] = None
    ) -> 'TransformationPipeline':
        """Add imputation step."""
        self.transformers.append(
            ImputationTransformer(strategy, fill_value, columns)
        )
        return self
    
    def add_feature_engineering(
        self,
        feature_functions: Dict[str, Callable]
    ) -> 'TransformationPipeline':
        """Add feature engineering step."""
        self.transformers.append(
            FeatureEngineeringTransformer(feature_functions)
        )
        return self
    
    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Fit and transform data through pipeline.
        
        Args:
            data: DataFrame to transform
            
        Returns:
            DataFrame: Transformed data
        """
        if not self.transformers:
            return data
        
        # Chain transformers
        for i in range(len(self.transformers) - 1):
            self.transformers[i].next_transformer = self.transformers[i + 1]
        
        # Run pipeline
        transformed = self.transformers[0].fit_transform(data)
        
        logger.info(
            f"Transformation pipeline completed",
            extra={
                "input_shape": data.shape,
                "output_shape": transformed.shape,
                "steps": len(self.transformers)
            }
        )
        
        return transformed
    
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data (must be fitted first).
        
        Args:
            data: DataFrame to transform
            
        Returns:
            DataFrame: Transformed data
        """
        if not self.transformers:
            return data
        
        # Chain transformers
        for i in range(len(self.transformers) - 1):
            self.transformers[i].next_transformer = self.transformers[i + 1]
        
        # Run pipeline
        transformed = self.transformers[0].transform(data)
        
        return transformed


# Export
__all__ = [
    "DataTransformer",
    "NormalizationTransformer",
    "EncodingTransformer",
    "FeatureEngineeringTransformer",
    "ImputationTransformer",
    "TransformationPipeline"
]
