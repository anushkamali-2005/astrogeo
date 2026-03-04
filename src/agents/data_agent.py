"""
Data Agent
==========
Intelligent agent for data operations:
- Data ingestion from various sources
- Data validation and quality checks
- Data preprocessing and cleaning
- Data profiling and statistics
- Schema inference

Author: Production Team
Version: 1.0.0
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic.v1 import BaseModel as LangChainBaseModel
from pydantic.v1 import Field as LangChainField

from src.agents.base_agent import BaseAgent
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# TOOL SCHEMAS
# ============================================================================


class IngestDataInput(LangChainBaseModel):
    """Input for ingest_data tool."""

    source_path: str = LangChainField(description="Path to data source (file, URL, database)")
    source_type: str = LangChainField(description="Type of source (csv, json, parquet, sql, s3)")
    options: Dict[str, Any] = LangChainField(
        default_factory=dict, description="Additional ingestion options"
    )


class ValidateDataInput(LangChainBaseModel):
    """Input for validate_data tool."""

    dataset_path: str = LangChainField(description="Path to dataset")
    validation_rules: Dict[str, Any] = LangChainField(
        default_factory=dict, description="Validation rules and constraints"
    )


class ProfileDataInput(LangChainBaseModel):
    """Input for profile_data tool."""

    dataset_path: str = LangChainField(description="Path to dataset")
    include_correlations: bool = LangChainField(
        default=True, description="Include correlation analysis"
    )


class CleanDataInput(LangChainBaseModel):
    """Input for clean_data tool."""

    dataset_path: str = LangChainField(description="Path to dataset")
    operations: List[str] = LangChainField(
        description="List of cleaning operations (remove_duplicates, handle_missing, etc.)"
    )


# ============================================================================
# DATA TOOLS
# ============================================================================


def ingest_data_tool(source_path: str, source_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest data from various sources - REAL IMPLEMENTATION.

    Args:
        source_path: Path to data source
        source_type: Type of source (csv, json, parquet, excel)
        options: Additional options

    Returns:
        dict: Ingestion results with statistics
    """
    import pandas as pd
    from pathlib import Path
    from uuid import uuid4
    import time
    
    logger.info(
        "Ingesting data via Data agent",
        extra={"source_path": source_path, "source_type": source_type},
    )

    try:
        start_time = time.time()
        path = Path(source_path)
        
        # Load based on type
        if source_type == "csv":
            df = pd.read_csv(path, **options)
        elif source_type == "json":
            df = pd.read_json(path, **options)
        elif source_type == "parquet":
            df = pd.read_parquet(path, **options)
        elif source_type == "excel":
            df = pd.read_excel(path, **options)
        else:
            return {
                "status": "error",
                "error": f"Unsupported source_type: {source_type}",
                "supported_types": ["csv", "json", "parquet", "excel"]
            }
        
        ingestion_time = time.time() - start_time
        
        # Generate statistics
        return {
            "status": "success",
            "dataset_id": str(uuid4()),
            "source_path": str(path),
            "source_type": source_type,
            "rows_ingested": len(df),
            "columns": list(df.columns),
            "num_columns": len(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "size_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "ingestion_time_seconds": round(ingestion_time, 3),
            "preview": df.head(3).to_dict('records'),
            "message": f"Successfully ingested {len(df)} rows from {source_path}"
        }
    except FileNotFoundError:
        logger.error(f"File not found: {source_path}")
        return {
            "status": "error",
            "error": "File not found",
            "source_path": source_path
        }
    except Exception as e:
        logger.error("Data ingestion failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "source_path": source_path,
            "source_type": source_type
        }


def validate_data_tool(dataset_path: str, validation_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate data quality and constraints - REAL IMPLEMENTATION.

    Args:
        dataset_path: Path to dataset
        validation_rules: Validation rules (schema, ranges, constraints)

    Returns:
        dict: Validation results
    """
    logger.info("Validating data via Data agent", extra={"dataset_path": dataset_path})

    try:
        import pandas as pd
        import numpy as np
        
        # Load data
        df = pd.read_csv(dataset_path)
        
        # Initialize results
        passed_checks = 0
        failed_checks = 0
        warnings = 0
        results = {}
        recommendations = []
        
        # 1. Schema Validation
        expected_columns = validation_rules.get("expected_columns", [])
        if expected_columns:
            actual_columns = list(df.columns)
            missing_cols = set(expected_columns) - set(actual_columns)
            extra_cols = set(actual_columns) - set(expected_columns)
            
            if missing_cols or extra_cols:
                failed_checks += 1
                results["schema_validation"] = {
                    "status": "failed",
                    "expected_columns": len(expected_columns),
                    "actual_columns": len(actual_columns),
                    "missing_columns": list(missing_cols),
                    "extra_columns": list(extra_cols)
                }
                if missing_cols:
                    recommendations.append(f"Missing columns: {', '.join(missing_cols)}")
            else:
                passed_checks += 1
                results["schema_validation"] = {
                    "status": "passed",
                    "expected_columns": len(expected_columns),
                    "actual_columns": len(actual_columns)
                }
        
        # 2. Data Types Validation
        expected_dtypes = validation_rules.get("expected_dtypes", {})
        if expected_dtypes:
            mismatches = []
            for col, expected_dtype in expected_dtypes.items():
                if col in df.columns:
                    actual_dtype = str(df[col].dtype)
                    if expected_dtype not in actual_dtype:
                        mismatches.append({
                            "column": col,
                            "expected": expected_dtype,
                            "actual": actual_dtype
                        })
            
            if mismatches:
                failed_checks += 1
                results["data_types"] = {
                    "status": "failed",
                    "mismatches": mismatches
                }
                recommendations.append(f"Fix data type mismatches in {len(mismatches)} columns")
            else:
                passed_checks += 1
                results["data_types"] = {"status": "passed", "mismatches": 0}
        
        # 3. Missing Values Check
        missing_threshold = validation_rules.get("max_missing_percent", 5.0)
        missing_cols = []
        total_missing = 0
        
        for col in df.columns:
            missing_pct = (df[col].isnull().sum() / len(df)) * 100
            if missing_pct > 0:
                missing_cols.append({"column": col, "missing_percent": round(missing_pct, 2)})
                total_missing += df[col].isnull().sum()
        
        total_missing_pct = (total_missing / (len(df) * len(df.columns))) * 100
        
        if total_missing_pct > missing_threshold:
            failed_checks += 1
            results["missing_values"] = {
                "status": "failed",
                "columns_with_missing": missing_cols,
                "total_missing_percent": round(total_missing_pct, 2),
                "threshold": missing_threshold
            }
            recommendations.append(f"Missing values ({total_missing_pct:.1f}%) exceed threshold ({missing_threshold}%)")
        elif len(missing_cols) > 0:
            warnings += 1
            results["missing_values"] = {
                "status": "warning",
                "columns_with_missing": missing_cols,
                "total_missing_percent": round(total_missing_pct, 2)
            }
            recommendations.append(f"Handle missing values in {len(missing_cols)} columns")
        else:
            passed_checks += 1
            results["missing_values"] = {
                "status": "passed",
                "columns_with_missing": [],
                "total_missing_percent": 0
            }
        
        # 4. Duplicate Rows Check
        duplicates = df.duplicated().sum()
        duplicate_pct = (duplicates / len(df)) * 100
        
        if duplicates > 0:
            if duplicate_pct > 1.0:
                failed_checks += 1
                results["duplicates"] = {
                    "status": "failed",
                    "duplicate_rows": int(duplicates),
                    "duplicate_percent": round(duplicate_pct, 2)
                }
                recommendations.append(f"Remove {duplicates} duplicate rows ({duplicate_pct:.1f}%)")
            else:
                warnings += 1
                results["duplicates"] = {
                    "status": "warning",
                    "duplicate_rows": int(duplicates),
                    "duplicate_percent": round(duplicate_pct, 2)
                }
                recommendations.append(f"Consider removing {duplicates} duplicate rows")
        else:
            passed_checks += 1
            results["duplicates"] = {
                "status": "passed",
                "duplicate_rows": 0,
                "duplicate_percent": 0
            }
        
        # 5. Outlier Detection (IQR method)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_info = []
        
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
            
            if outliers > 0:
                outlier_pct = (outliers / len(df)) * 100
                outlier_info.append({
                    "column": col,
                    "outlier_count": int(outliers),
                    "outlier_percent": round(outlier_pct, 2)
                })
        
        if outlier_info:
            total_outliers = sum(o["outlier_count"] for o in outlier_info)
            warnings += 1
            results["outliers"] = {
                "status": "warning",
                "columns_with_outliers": outlier_info,
                "total_outlier_count": total_outliers
            }
            recommendations.append(f"Investigate outliers in {len(outlier_info)} numeric columns")
        else:
            passed_checks += 1
            results["outliers"] = {
                "status": "passed",
                "columns_with_outliers": [],
                "total_outlier_count": 0
            }
        
        # 6. Value Range Validation
        value_ranges = validation_rules.get("value_ranges", {})
        range_violations = []
        
        for col, (min_val, max_val) in value_ranges.items():
            if col in df.columns and df[col].dtype in [np.float64, np.int64]:
                violations = ((df[col] < min_val) | (df[col] > max_val)).sum()
                if violations > 0:
                    range_violations.append({
                        "column": col,
                        "expected_range": [min_val, max_val],
                        "violations": int(violations)
                    })
        
        if range_violations:
            failed_checks += 1
            results["value_ranges"] = {
                "status": "failed",
                "violations": range_violations
            }
            recommendations.append(f"Fix value range violations in {len(range_violations)} columns")
        elif value_ranges:
            passed_checks += 1
            results["value_ranges"] = {
                "status": "passed",
                "all_within_expected_ranges": True
            }
        
        # Overall validation status
        total_checks = passed_checks + failed_checks + warnings
        validation_passed = failed_checks == 0
        
        return {
            "status": "success",
            "dataset_path": dataset_path,
            "validation_passed": validation_passed,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "results": results,
            "recommendations": recommendations if recommendations else ["All validation checks passed!"],
            "message": f"Data validation completed with {failed_checks} failures and {warnings} warnings",
        }
    except Exception as e:
        logger.error("Data validation failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "dataset_path": dataset_path
        }


def profile_data_tool(dataset_path: str, include_correlations: bool = True) -> Dict[str, Any]:
    """
    Generate comprehensive data profile and statistics - REAL IMPLEMENTATION.

    Args:
        dataset_path: Path to dataset
        include_correlations: Include correlation analysis

    Returns:
        dict: Data profiling results
    """
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    logger.info("Profiling data via Data agent", extra={"dataset_path": dataset_path})

    try:
        # Load data
        path = Path(dataset_path)
        if path.suffix == '.csv':
            df = pd.read_csv(path)
        elif path.suffix == '.parquet':
            df = pd.read_parquet(path)
        elif path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)  # Default to CSV
        
        # Basic statistics
        numeric_stats = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            numeric_stats[col] = {
                "count": int(df[col].count()),
                "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                "std": float(df[col].std()) if not pd.isna(df[col].std()) else None,
                "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                "q25": float(df[col].quantile(0.25)) if not pd.isna(df[col].quantile(0.25)) else None,
                "q50": float(df[col].quantile(0.50)) if not pd.isna(df[col].quantile(0.50)) else None,
                "q75": float(df[col].quantile(0.75)) if not pd.isna(df[col].quantile(0.75)) else None,
                "missing": int(df[col].isna().sum()),
                "missing_percent": float(df[col].isna().sum() / len(df) * 100)
            }
        
        # Categorical statistics
        categorical_stats = {}
        for col in df.select_dtypes(include=['object', 'category']).columns:
            value_counts = df[col].value_counts()
            categorical_stats[col] = {
                "count": int(df[col].count()),
                "unique": int(df[col].nunique()),
                "top": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "freq": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "missing": int(df[col].isna().sum()),
                "missing_percent": float(df[col].isna().sum() / len(df) * 100),
                "value_counts": value_counts.head(10).to_dict()
            }
        
        # Correlations
        correlations = None
        if include_correlations and len(df.select_dtypes(include=[np.number]).columns) > 1:
            corr_matrix = df.select_dtypes(include=[np.number]).corr()
            # Get significant correlations
            correlations = {}
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    col1 = corr_matrix.columns[i]
                    col2 = corr_matrix.columns[j]
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.5:  # Only significant correlations
                        correlations[f"{col1}_{col2}"] = float(corr_value)
        
        # Data quality score
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isna().sum().sum()
        duplicate_rows = df.duplicated().sum()
        quality_score = 100 - ((missing_cells / total_cells) * 100) - ((duplicate_rows / len(df)) * 10)
        
        # Generate recommendations
        recommendations = []
        if missing_cells > 0:
            recommendations.append(f"Handle {missing_cells} missing values across columns")
        if duplicate_rows > 0:
            recommendations.append(f"Remove {duplicate_rows} duplicate rows")
        if len(categorical_stats) > 0:
            recommendations.append("Consider encoding categorical variables")
        if correlations:
            for pair, corr in list(correlations.items())[:3]:
                recommendations.append(f"{pair.replace('_', ' and ')} are correlated ({corr:.2f})")
        
        return {
            "status": "success",
            "dataset_path": dataset_path,
            "overview": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
                "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
                "categorical_columns": len(df.select_dtypes(include=['object', 'category']).columns),
                "datetime_columns": len(df.select_dtypes(include=['datetime64']).columns),
                "missing_values_total": int(missing_cells),
                "duplicate_rows": int(duplicate_rows),
            },
            "numeric_statistics": numeric_stats,
            "categorical_statistics": categorical_stats,
            "correlations": correlations,
            "data_quality_score": float(max(0, min(100, quality_score))),
            "recommendations": recommendations if recommendations else ["Data quality looks good!"],
            "message": "Data profiling completed successfully"
        }
    except Exception as e:
        logger.error("Data profiling failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "dataset_path": dataset_path
        }


def clean_data_tool(dataset_path: str, operations: List[str]) -> Dict[str, Any]:
    """
    Clean and preprocess data - REAL IMPLEMENTATION.

    Args:
        dataset_path: Path to dataset
        operations: List of cleaning operations (remove_duplicates, fill_missing, remove_outliers)

    Returns:
        dict: Cleaning results
    """
    logger.info(
        "Cleaning data via Data agent",
        extra={"dataset_path": dataset_path, "operations": operations},
    )

    try:
        import pandas as pd
        import numpy as np
        from pathlib import Path
        
        # Load data
        df = pd.read_csv(dataset_path)
        
        # Track before stats
        before_stats = {
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": int(df.isnull().sum().sum()),
            "duplicates": int(df.duplicated().sum())
        }
        
        # Track changes
        changes = {
            "removed_duplicates": 0,
            "filled_missing_values": 0,
            "removed_outliers": 0,
            "normalized_columns": [],
            "encoded_columns": []
        }
        
        # Perform operations
        for operation in operations:
            if operation == "remove_duplicates":
                duplicates_before = df.duplicated().sum()
                df = df.drop_duplicates()
                changes["removed_duplicates"] = int(duplicates_before)
                
            elif operation == "fill_missing":
                missing_before = df.isnull().sum().sum()
                # Fill numeric with median, categorical with mode
                for col in df.columns:
                    if df[col].dtype in [np.float64, np.int64]:
                        df[col].fillna(df[col].median(), inplace=True)
                    else:
                        mode_val = df[col].mode()[0] if not df[col].mode().empty else "Unknown"
                        df[col].fillna(mode_val, inplace=True)
                changes["filled_missing_values"] = int(missing_before)
                
            elif operation == "remove_outliers":
                # Remove outliers using IQR method for numeric columns
                outliers_removed = 0
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    before_len = len(df)
                    df = df[~((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR)))]
                    outliers_removed += before_len - len(df)
                changes["removed_outliers"] = outliers_removed
        
        # After stats
        after_stats = {
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": int(df.isnull().sum().sum()),
            "duplicates": int(df.duplicated().sum())
        }
        
        # Calculate quality scores
        before_score = 100 - (before_stats["missing_values"] / (before_stats["rows"] * before_stats["columns"]) * 100)
        after_score = 100 - (after_stats["missing_values"] / max(1, after_stats["rows"] * after_stats["columns"]) * 100)
        
        # Save cleaned data
        output_path = dataset_path.replace(".csv", "_cleaned.csv")
        df.to_csv(output_path, index=False)
        
        return {
            "status": "success",
            "dataset_path": dataset_path,
            "output_path": output_path,
            "operations_performed": operations,
            "before": before_stats,
            "after": after_stats,
            "changes": changes,
            "quality_improvement": {
                "before_score": round(before_score, 2),
                "after_score": round(after_score, 2),
                "improvement_percent": round(after_score - before_score, 2),
            },
            "message": "Data cleaning completed successfully",
        }
    except Exception as e:
        logger.error("Data cleaning failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "dataset_path": dataset_path
        }


def transform_data_tool(dataset_path: str, transformations: List[str]) -> Dict[str, Any]:
    """
    Transform data with various operations - REAL IMPLEMENTATION.

    Args:
        dataset_path: Path to dataset
        transformations: List of transformations (normalize, encode_categorical, create_features)

    Returns:
        dict: Transformation results
    """
    logger.info("Transforming data via Data agent", extra={"dataset_path": dataset_path})

    try:
        import pandas as pd
        import numpy as np
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        
        # Load data
        df = pd.read_csv(dataset_path)
        original_columns = df.columns.tolist()
        
        new_columns = []
        modified_columns = []
        
        # Perform transformations
        for transformation in transformations:
            if transformation == "normalize":
                # Normalize numeric columns
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                scaler = StandardScaler()
                for col in numeric_cols:
                    df[f"{col}_normalized"] = scaler.fit_transform(df[[col]])
                    new_columns.append(f"{col}_normalized")
                    
            elif transformation == "encode_categorical":
                # Encode categorical columns
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns
                for col in categorical_cols:
                    le = LabelEncoder()
                    df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
                    new_columns.append(f"{col}_encoded")
                    
            elif transformation == "create_features":
                # Create feature engineering examples
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) >= 2:
                    # Create interaction features
                    col1, col2 = numeric_cols[0], numeric_cols[1]
                    df[f"{col1}_{col2}_interaction"] = df[col1] * df[col2]
                    df[f"{col1}_{col2}_ratio"] = df[col1] / (df[col2] + 1e-10)
                    new_columns.extend([f"{col1}_{col2}_interaction", f"{col1}_{col2}_ratio"])
                    
            elif transformation == "datetime_features":
                # Extract datetime features
                date_cols = df.select_dtypes(include=['datetime64']).columns
                for col in date_cols:
                    df[f"{col}_year"] = df[col].dt.year
                    df[f"{col}_month"] = df[col].dt.month
                    df[f"{col}_day"] = df[col].dt.day
                    df[f"{col}_dayofweek"] = df[col].dt.dayofweek
                    new_columns.extend([f"{col}_year", f"{col}_month", f"{col}_day", f"{col}_dayofweek"])
                    modified_columns.append(col)
        
        # Save transformed data
        output_path = dataset_path.replace(".csv", "_transformed.csv")
        df.to_csv(output_path, index=False)
        
        return {
            "status": "success",
            "dataset_path": dataset_path,
            "output_path": output_path,
            "transformations_applied": transformations,
            "new_columns_created": new_columns,
            "columns_modified": modified_columns,
            "original_columns": len(original_columns),
            "final_columns": len(df.columns),
            "message": "Data transformation completed successfully",
        }
    except Exception as e:
        logger.error("Data transformation failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "dataset_path": dataset_path
        }


def merge_datasets_tool(
    dataset_paths: List[str], merge_strategy: str, join_keys: List[str]
) -> Dict[str, Any]:
    """
    Merge multiple datasets - REAL IMPLEMENTATION.

    Args:
        dataset_paths: List of dataset paths
        merge_strategy: Merge strategy (inner, outer, left, right)
        join_keys: Keys to join on

    Returns:
        dict: Merge results
    """
    logger.info(
        "Merging datasets via Data agent",
        extra={"num_datasets": len(dataset_paths), "strategy": merge_strategy},
    )

    try:
        import pandas as pd
        
        if len(dataset_paths) < 2:
            return {
                "status": "error",
                "error": "Need at least 2 datasets to merge"
            }
        
        # Load all datasets
        dataframes = []
        before_stats = {}
        for i, path in enumerate(dataset_paths):
            df = pd.read_csv(path)
            dataframes.append(df)
            before_stats[f"dataset_{i+1}_rows"] = len(df)
            before_stats[f"dataset_{i+1}_columns"] = len(df.columns)
        
        # Merge datasets sequentially
        merged_df = dataframes[0]
        for i in range(1, len(dataframes)):
            merged_df = pd.merge(
                merged_df,
                dataframes[i],
                on=join_keys,
                how=merge_strategy
            )
        
        # Calculate after stats
        matched_rows = len(merged_df)
        unmatched_rows = sum(before_stats[f"dataset_{i+1}_rows"] for i in range(len(dataset_paths))) - matched_rows
        
        # Save merged dataset
        output_path = "data/processed/merged_dataset.csv"
        merged_df.to_csv(output_path, index=False)
        
        return {
            "status": "success",
            "input_datasets": dataset_paths,
            "output_path": output_path,
            "merge_strategy": merge_strategy,
            "join_keys": join_keys,
            "before": before_stats,
            "after": {
                "merged_rows": matched_rows,
                "merged_columns": len(merged_df.columns),
                "matched_rows": matched_rows,
                "unmatched_rows": max(0, unmatched_rows),
            },
            "message": f"Successfully merged {len(dataset_paths)} datasets using {merge_strategy} join",
        }
    except Exception as e:
        logger.error("Dataset merge failed", error=e)
        return {
            "status": "error",
            "error": str(e),
            "dataset_paths": dataset_paths
        }


# ============================================================================
# DATA AGENT
# ============================================================================


class DataAgent(BaseAgent):
    """
    Intelligent agent for data operations.

    Capabilities:
    - Ingest data from multiple sources
    - Validate data quality
    - Profile and analyze datasets
    - Clean and preprocess data
    - Transform and merge datasets
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3, **kwargs):
        """
        Initialize Data Agent.

        Args:
            model: LLM model name
            temperature: LLM temperature
            **kwargs: Additional base agent arguments
        """
        # Create tools
        tools = self._create_tools()

        # Initialize base agent
        super().__init__(
            name="DataAgent",
            description="Intelligent agent for data operations and ETL",
            tools=tools,
            model=model,
            temperature=temperature,
            **kwargs,
        )

        logger.info("Data Agent initialized", extra={"num_tools": len(tools)})

    def _create_tools(self) -> List[BaseTool]:
        """
        Create data-specific tools.

        Returns:
            list: List of LangChain tools
        """
        # Create data agent tools
        tools: list[BaseTool] = [
            StructuredTool.from_function(
                func=ingest_data_tool,
                name="ingest_data",
                description="Ingest data from various sources (CSV, JSON, Parquet, SQL, S3). "
                "Use when user wants to load or import data.",
                args_schema=IngestDataInput,
            ),
            StructuredTool.from_function(
                func=validate_data_tool,
                name="validate_data",
                description="Validate data quality, check schema, detect issues. "
                "Use when user wants to check data quality or find problems.",
                args_schema=ValidateDataInput,
            ),
            StructuredTool.from_function(
                func=profile_data_tool,
                name="profile_data",
                description="Generate comprehensive data statistics and profiling report. "
                "Use when user wants to understand their data.",
                args_schema=ProfileDataInput,
            ),
            StructuredTool.from_function(
                func=clean_data_tool,
                name="clean_data",
                description="Clean and preprocess data (remove duplicates, handle missing values). "
                "Use when user wants to clean or prepare data.",
                args_schema=CleanDataInput,
            ),
            StructuredTool.from_function(
                func=transform_data_tool,
                name="transform_data",
                description="Transform data with various operations (normalization, encoding, aggregation). "
                "Use when user wants to modify or engineer features.",
            ),
            StructuredTool.from_function(
                func=merge_datasets_tool,
                name="merge_datasets",
                description="Merge or join multiple datasets together. "
                "Use when user wants to combine data from different sources.",
            ),
        ]

        return tools

    def _get_system_prompt(self) -> str:
        """
        Get Data Agent system prompt.

        Returns:
            str: System prompt
        """
        return """You are an expert Data Engineer agent specialized in data operations and ETL pipelines.

Your capabilities:
- Ingest data from various sources (CSV, JSON, Parquet, SQL, S3, APIs)
- Validate data quality and detect issues
- Profile datasets and generate statistics
- Clean and preprocess data
- Transform data and engineer features
- Merge and join datasets

Guidelines:
1. Always validate data before processing
2. Provide clear statistics and insights
3. Recommend best practices for data quality
4. Explain data issues in simple terms
5. Suggest optimal data transformations

When working with data:
- Check for missing values, duplicates, and outliers
- Validate data types and schemas
- Calculate descriptive statistics
- Identify correlations and patterns
- Recommend cleaning strategies

Data Quality Checks:
- Schema validation (column names, data types)
- Missing values detection
- Duplicate records identification
- Outlier detection
- Value range validation
- Referential integrity checks

Be thorough, accurate, and always prioritize data quality."""


# Example usage
if __name__ == "__main__":
    import asyncio

    async def demo():
        # Initialize agent
        agent = DataAgent()

        # Execute task
        result = await agent.execute(
            task="Ingest and validate the customer data from customers.csv, "
            "then provide a data quality report"
        )

        print(json.dumps(result, indent=2))

    asyncio.run(demo())


# Export
__all__ = ["DataAgent"]
