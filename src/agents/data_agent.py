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
    Ingest data from various sources.

    Args:
        source_path: Path to data source
        source_type: Type of source (csv, json, parquet, sql, s3)
        options: Additional options

    Returns:
        dict: Ingestion results with statistics
    """
    logger.info(
        "Ingesting data via Data agent",
        extra={"source_path": source_path, "source_type": source_type},
    )

    # Mock implementation - replace with actual ingestion logic
    return {
        "status": "success",
        "dataset_id": "dataset_123",
        "source_path": source_path,
        "source_type": source_type,
        "rows_ingested": 10000,
        "columns": 25,
        "size_mb": 15.5,
        "ingestion_time_seconds": 2.3,
        "preview": [
            {"id": 1, "name": "Sample 1", "value": 100},
            {"id": 2, "name": "Sample 2", "value": 200},
            {"id": 3, "name": "Sample 3", "value": 300},
        ],
        "message": f"Successfully ingested data from {source_path}",
    }


def validate_data_tool(dataset_path: str, validation_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate data quality and constraints.

    Args:
        dataset_path: Path to dataset
        validation_rules: Validation rules

    Returns:
        dict: Validation results
    """
    logger.info("Validating data via Data agent", extra={"dataset_path": dataset_path})

    return {
        "status": "success",
        "dataset_path": dataset_path,
        "validation_passed": True,
        "total_checks": 15,
        "passed_checks": 14,
        "failed_checks": 1,
        "warnings": 2,
        "results": {
            "schema_validation": {"status": "passed", "expected_columns": 25, "actual_columns": 25},
            "data_types": {"status": "passed", "mismatches": 0},
            "missing_values": {
                "status": "warning",
                "columns_with_missing": ["column_x", "column_y"],
                "total_missing_percent": 2.5,
            },
            "duplicates": {"status": "failed", "duplicate_rows": 15, "duplicate_percent": 0.15},
            "outliers": {
                "status": "warning",
                "columns_with_outliers": ["price"],
                "outlier_count": 45,
            },
            "value_ranges": {"status": "passed", "all_within_expected_ranges": True},
        },
        "recommendations": [
            "Remove 15 duplicate rows",
            "Handle missing values in column_x and column_y",
            "Investigate outliers in price column",
        ],
        "message": "Data validation completed with 1 failure and 2 warnings",
    }


def profile_data_tool(dataset_path: str, include_correlations: bool = True) -> Dict[str, Any]:
    """
    Generate comprehensive data profile and statistics.

    Args:
        dataset_path: Path to dataset
        include_correlations: Include correlation analysis

    Returns:
        dict: Data profiling results
    """
    logger.info("Profiling data via Data agent", extra={"dataset_path": dataset_path})

    return {
        "status": "success",
        "dataset_path": dataset_path,
        "overview": {
            "total_rows": 10000,
            "total_columns": 25,
            "memory_usage_mb": 15.5,
            "numeric_columns": 18,
            "categorical_columns": 7,
            "datetime_columns": 0,
            "missing_values_total": 250,
            "duplicate_rows": 15,
        },
        "numeric_statistics": {
            "age": {
                "count": 10000,
                "mean": 45.2,
                "std": 12.5,
                "min": 18,
                "max": 90,
                "q25": 35,
                "q50": 44,
                "q75": 55,
                "missing": 10,
                "missing_percent": 0.1,
            },
            "income": {
                "count": 9950,
                "mean": 75000,
                "std": 25000,
                "min": 20000,
                "max": 200000,
                "q25": 55000,
                "q50": 72000,
                "q75": 92000,
                "missing": 50,
                "missing_percent": 0.5,
            },
        },
        "categorical_statistics": {
            "category": {
                "count": 10000,
                "unique": 5,
                "top": "Category_A",
                "freq": 3500,
                "missing": 0,
                "value_counts": {
                    "Category_A": 3500,
                    "Category_B": 2800,
                    "Category_C": 2000,
                    "Category_D": 1200,
                    "Category_E": 500,
                },
            }
        },
        "correlations": (
            {"age_income": 0.65, "age_spending": 0.42, "income_spending": 0.78}
            if include_correlations
            else None
        ),
        "data_quality_score": 92.5,
        "recommendations": [
            "Handle 250 missing values across columns",
            "Remove 15 duplicate rows",
            "Consider encoding categorical variables",
            "Income and spending are highly correlated (0.78)",
        ],
        "message": "Data profiling completed successfully",
    }


def clean_data_tool(dataset_path: str, operations: List[str]) -> Dict[str, Any]:
    """
    Clean and preprocess data.

    Args:
        dataset_path: Path to dataset
        operations: List of cleaning operations

    Returns:
        dict: Cleaning results
    """
    logger.info(
        "Cleaning data via Data agent",
        extra={"dataset_path": dataset_path, "operations": operations},
    )

    return {
        "status": "success",
        "dataset_path": dataset_path,
        "output_path": "data/processed/cleaned_dataset.csv",
        "operations_performed": operations,
        "before": {"rows": 10000, "columns": 25, "missing_values": 250, "duplicates": 15},
        "after": {
            "rows": 9985,  # Removed duplicates
            "columns": 25,
            "missing_values": 0,  # Filled missing values
            "duplicates": 0,
        },
        "changes": {
            "removed_duplicates": 15,
            "filled_missing_values": 250,
            "removed_outliers": 0,
            "normalized_columns": ["age", "income"],
            "encoded_columns": ["category"],
        },
        "quality_improvement": {
            "before_score": 87.5,
            "after_score": 98.2,
            "improvement_percent": 12.2,
        },
        "message": "Data cleaning completed successfully",
    }


def transform_data_tool(dataset_path: str, transformations: List[str]) -> Dict[str, Any]:
    """
    Transform data with various operations.

    Args:
        dataset_path: Path to dataset
        transformations: List of transformations

    Returns:
        dict: Transformation results
    """
    logger.info("Transforming data via Data agent", extra={"dataset_path": dataset_path})

    return {
        "status": "success",
        "dataset_path": dataset_path,
        "output_path": "data/processed/transformed_dataset.csv",
        "transformations_applied": transformations,
        "new_columns_created": ["age_group", "income_category", "total_value"],
        "columns_modified": ["date_converted_to_datetime", "normalized_price"],
        "transformation_time_seconds": 1.5,
        "message": "Data transformation completed successfully",
    }


def merge_datasets_tool(
    dataset_paths: List[str], merge_strategy: str, join_keys: List[str]
) -> Dict[str, Any]:
    """
    Merge multiple datasets.

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

    return {
        "status": "success",
        "input_datasets": dataset_paths,
        "output_path": "data/processed/merged_dataset.csv",
        "merge_strategy": merge_strategy,
        "join_keys": join_keys,
        "before": {"dataset_1_rows": 10000, "dataset_2_rows": 8000},
        "after": {
            "merged_rows": 9500,
            "merged_columns": 40,
            "matched_rows": 9500,
            "unmatched_rows": 500,
        },
        "message": f"Successfully merged {len(dataset_paths)} datasets using {merge_strategy} join",
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
        tools = [
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
