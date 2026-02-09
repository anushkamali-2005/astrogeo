"""
Data Validators
================
Production-level data validation pipeline using chain of responsibility pattern.

Validators:
- Schema validation (column types, names)
- Quality validation (completeness, uniqueness)
- Geospatial validation (coordinate validity)
- Business rule validation

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import numpy as np

from src.core.logging import get_logger
from src.core.exceptions import ValidationError


logger = get_logger(__name__)


# ============================================================================
# VALIDATION RESULT
# ============================================================================

class ValidationLevel(str, Enum):
    """Validation level enum."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue."""
    level: ValidationLevel
    field: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Validation result container."""
    valid: bool
    issues: List[ValidationIssue]
    
    def add_issue(
        self,
        level: ValidationLevel,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add validation issue."""
        self.issues.append(
            ValidationIssue(level=level, field=field, message=message, details=details)
        )
        
        if level == ValidationLevel.ERROR:
            self.valid = False
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get error-level issues."""
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get warning-level issues."""
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]


# ============================================================================
# BASE VALIDATOR
# ============================================================================

class DataValidator(ABC):
    """
    Abstract base validator with chain of responsibility pattern.
    
    Design Pattern: Chain of Responsibility
    """
    
    def __init__(self, next_validator: Optional['DataValidator'] = None):
        """
        Initialize validator.
        
        Args:
            next_validator: Next validator in chain
        """
        self.next_validator = next_validator
    
    async def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate data and chain to next validator.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            ValidationResult: Validation result
        """
        # Run this validator
        result = await self._validate_impl(data)
        
        # Chain to next validator
        if self.next_validator:
            next_result = await self.next_validator.validate(data)
            result.issues.extend(next_result.issues)
            result.valid = result.valid and next_result.valid
        
        return result
    
    @abstractmethod
    async def _validate_impl(self, data: pd.DataFrame) -> ValidationResult:
        """
        Implement specific validation logic.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            ValidationResult: Validation result
        """
        pass


# ============================================================================
# SCHEMA VALIDATOR
# ============================================================================

class SchemaValidator(DataValidator):
    """
    Validates data schema (columns, types).
    """
    
    def __init__(
        self,
        required_columns: Optional[List[str]] = None,
        column_types: Optional[Dict[str, type]] = None,
        next_validator: Optional[DataValidator] = None
    ):
        """
        Initialize schema validator.
        
        Args:
            required_columns: Required column names
            column_types: Expected column data types
            next_validator: Next validator in chain
        """
        super().__init__(next_validator)
        self.required_columns = required_columns or []
        self.column_types = column_types or {}
    
    async def _validate_impl(self, data: pd.DataFrame) -> ValidationResult:
        """Validate data schema."""
        result = ValidationResult(valid=True, issues=[])
        
        # Check required columns
        missing_columns = set(self.required_columns) - set(data.columns)
        if missing_columns:
            result.add_issue(
                level=ValidationLevel.ERROR,
                message=f"Missing required columns: {missing_columns}",
                details={"missing_columns": list(missing_columns)}
            )
        
        # Check column types
        for col, expected_type in self.column_types.items():
            if col in data.columns:
                actual_type = data[col].dtype
                if not pd.api.types.is_dtype_equal(actual_type, expected_type):
                    result.add_issue(
                        level=ValidationLevel.WARNING,
                        field=col,
                        message=f"Type mismatch for {col}: expected {expected_type}, got {actual_type}",
                        details={"expected": str(expected_type), "actual": str(actual_type)}
                    )
        
        logger.debug(f"Schema validation completed: {result.valid}")
        return result


# ============================================================================
# QUALITY VALIDATOR
# ============================================================================

class QualityValidator(DataValidator):
    """
    Validates data quality (completeness, uniqueness).
    """
    
    def __init__(
        self,
        max_missing_percent: float = 20.0,
        unique_columns: Optional[List[str]] = None,
        next_validator: Optional[DataValidator] = None
    ):
        """
        Initialize quality validator.
        
        Args:
            max_missing_percent: Maximum allowed missing data percentage
            unique_columns: Columns that should have unique values
            next_validator: Next validator in chain
        """
        super().__init__(next_validator)
        self.max_missing_percent = max_missing_percent
        self.unique_columns = unique_columns or []
    
    async def _validate_impl(self, data: pd.DataFrame) -> ValidationResult:
        """Validate data quality."""
        result = ValidationResult(valid=True, issues=[])
        
        # Check missing data
        for col in data.columns:
            missing_pct = (data[col].isna().sum() / len(data)) * 100
            if missing_pct > self.max_missing_percent:
                result.add_issue(
                    level=ValidationLevel.WARNING,
                    field=col,
                    message=f"High missing data: {missing_pct:.1f}% in {col}",
                    details={"missing_percent": missing_pct}
                )
        
        # Check uniqueness
        for col in self.unique_columns:
            if col in data.columns:
                duplicates = data[col].duplicated().sum()
                if duplicates > 0:
                    result.add_issue(
                        level=ValidationLevel.ERROR,
                        field=col,
                        message=f"Duplicate values found in {col}: {duplicates} duplicates",
                        details={"duplicate_count": duplicates}
                    )
        
        # Check for empty dataframe
        if len(data) == 0:
            result.add_issue(
                level=ValidationLevel.ERROR,
                message="Dataset is empty",
                details={"row_count": 0}
            )
        
        logger.debug(f"Quality validation completed: {result.valid}")
        return result


# ============================================================================
# GEOSPATIAL VALIDATOR
# ============================================================================

class GeospatialValidator(DataValidator):
    """
    Validates geospatial data (coordinates, geometries).
    """
    
    def __init__(
        self,
        latitude_column: str = "latitude",
        longitude_column: str = "longitude",
        next_validator: Optional[DataValidator] = None
    ):
        """
        Initialize geospatial validator.
        
        Args:
            latitude_column: Latitude column name
            longitude_column: Longitude column name
            next_validator: Next validator in chain
        """
        super().__init__(next_validator)
        self.latitude_column = latitude_column
        self.longitude_column = longitude_column
    
    async def _validate_impl(self, data: pd.DataFrame) -> ValidationResult:
        """Validate geospatial data."""
        result = ValidationResult(valid=True, issues=[])
        
        # Check if geospatial columns exist
        if self.latitude_column not in data.columns or self.longitude_column not in data.columns:
            return result  # Not a geospatial dataset
        
        # Validate latitude range (-90 to 90)
        invalid_lat = (
            (data[self.latitude_column] < -90) |
            (data[self.latitude_column] > 90)
        ).sum()
        
        if invalid_lat > 0:
            result.add_issue(
                level=ValidationLevel.ERROR,
                field=self.latitude_column,
                message=f"Invalid latitude values: {invalid_lat} values out of range [-90, 90]",
                details={"invalid_count": invalid_lat}
            )
        
        # Validate longitude range (-180 to 180)
        invalid_lon = (
            (data[self.longitude_column] < -180) |
            (data[self.longitude_column] > 180)
        ).sum()
        
        if invalid_lon > 0:
            result.add_issue(
                level=ValidationLevel.ERROR,
                field=self.longitude_column,
                message=f"Invalid longitude values: {invalid_lon} values out of range [-180, 180]",
                details={"invalid_count": invalid_lon}
            )
        
        logger.debug(f"Geospatial validation completed: {result.valid}")
        return result


# ============================================================================
# VALIDATION PIPELINE
# ============================================================================

class ValidationPipeline:
    """
    Fluent builder for validation pipeline.
    
    Design Pattern: Builder
    """
    
    def __init__(self):
        """Initialize validation pipeline."""
        self.validators: List[DataValidator] = []
    
    def add_schema_validation(
        self,
        required_columns: Optional[List[str]] = None,
        column_types: Optional[Dict[str, type]] = None
    ) -> 'ValidationPipeline':
        """Add schema validation."""
        self.validators.append(
            SchemaValidator(required_columns, column_types)
        )
        return self
    
    def add_quality_validation(
        self,
        max_missing_percent: float = 20.0,
        unique_columns: Optional[List[str]] = None
    ) -> 'ValidationPipeline':
        """Add quality validation."""
        self.validators.append(
            QualityValidator(max_missing_percent, unique_columns)
        )
        return self
    
    def add_geospatial_validation(
        self,
        latitude_column: str = "latitude",
        longitude_column: str = "longitude"
    ) -> 'ValidationPipeline':
        """Add geospatial validation."""
        self.validators.append(
            GeospatialValidator(latitude_column, longitude_column)
        )
        return self
    
    async def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Run all validators in pipeline.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            ValidationResult: Combined validation result
        """
        # Chain validators
        if not self.validators:
            return ValidationResult(valid=True, issues=[])
        
        # Create chain
        for i in range(len(self.validators) - 1):
            self.validators[i].next_validator = self.validators[i + 1]
        
        # Run validation chain
        result = await self.validators[0].validate(data)
        
        logger.info(
            f"Validation pipeline completed",
            extra={
                "valid": result.valid,
                "errors": len(result.get_errors()),
                "warnings": len(result.get_warnings())
            }
        )
        
        return result


# Export
__all__ = [
    "DataValidator",
    "SchemaValidator",
    "QualityValidator",
    "GeospatialValidator",
    "ValidationPipeline",
    "ValidationResult",
    "ValidationIssue",
    "ValidationLevel"
]
