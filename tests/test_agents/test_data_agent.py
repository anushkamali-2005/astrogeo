import pytest
import pandas as pd
import sys
import os
sys.path.append(os.getcwd())
from src.agents.data_agent import (
    ingest_data_tool,
    profile_data_tool,
    validate_data_tool,
    clean_data_tool,
    transform_data_tool,
    merge_datasets_tool
)

@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 1],  # Duplicate ID
        "name": ["Alice", "Bob", "Charlie", "David", "Alice"],
        "age": [25, 30, 35, 100, 25],  # Outlier age
        "salary": [50000, 60000, None, 80000, 50000],  # Missing salary
        "department": ["HR", "IT", "Finance", "IT", "HR"]
    })
    path = tmp_path / "test_data.csv"
    df.to_csv(path, index=False)
    return str(path)

@pytest.fixture
def sample_csv_2(tmp_path):
    """Create a second sample CSV file for merging."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "bonus": [5000, 6000, 7000]
    })
    path = tmp_path / "test_data_2.csv"
    df.to_csv(path, index=False)
    return str(path)

def test_ingest_data_tool(sample_csv):
    """Test data ingestion tool."""
    result = ingest_data_tool(sample_csv, "csv", {})
    assert result["status"] == "success"
    assert result["rows_ingested"] == 5
    assert len(result["columns"]) == 5
    assert "id" in result["columns"]
    assert "salary" in result["columns"]

def test_profile_data_tool(sample_csv):
    """Test data profiling tool."""
    result = profile_data_tool(sample_csv)
    assert result["status"] == "success"
    assert result["overview"]["total_rows"] == 5
    assert result["overview"]["missing_values_total"] > 0
    assert result["overview"]["duplicate_rows"] > 0
    assert "numeric_statistics" in result
    assert "categorical_statistics" in result

def test_validate_data_tool(sample_csv):
    """Test data validation tool."""
    rules = {
        "expected_columns": ["id", "name", "age", "salary", "department"],
        "value_ranges": {"age": [0, 90]},
        "max_missing_percent": 10.0
    }
    result = validate_data_tool(sample_csv, rules)
    assert result["status"] == "success"
    # Should fail due to outlier age (100 > 90) and duplicates
    assert result["failed_checks"] > 0 or result["warnings"] > 0
    assert result["results"]["schema_validation"]["status"] == "passed"
    assert result["results"]["value_ranges"]["status"] == "failed"

def test_clean_data_tool(sample_csv):
    """Test data cleaning tool."""
    operations = ["remove_duplicates", "fill_missing", "remove_outliers"]
    result = clean_data_tool(sample_csv, operations)
    assert result["status"] == "success"
    assert result["changes"]["removed_duplicates"] == 1
    assert result["changes"]["filled_missing_values"] > 0
    
    # Verify cleaned file
    cleaned_df = pd.read_csv(result["output_path"])
    assert len(cleaned_df) < 5  # Duplicates removed
    assert cleaned_df["salary"].isnull().sum() == 0  # Missing filled

def test_transform_data_tool(sample_csv):
    """Test data transformation tool."""
    transformations = ["normalize", "encode_categorical", "create_features"]
    result = transform_data_tool(sample_csv, transformations)
    assert result["status"] == "success"
    assert "age_normalized" in result["new_columns_created"]
    assert "department_encoded" in result["new_columns_created"]
    
    # Verify transformed file
    transformed_df = pd.read_csv(result["output_path"])
    assert "age_normalized" in transformed_df.columns
    assert "department_encoded" in transformed_df.columns

def test_merge_datasets_tool(sample_csv, sample_csv_2):
    """Test dataset merging tool."""
    result = merge_datasets_tool(
        [sample_csv, sample_csv_2], 
        "inner", 
        ["id"]
    )
    assert result["status"] == "success"
    assert result["after"]["merged_rows"] == 3  # Intersection of IDs [1,2,3]
    
    # Verify merged file
    merged_df = pd.read_csv(result["output_path"])
    assert "bonus" in merged_df.columns
    assert "salary" in merged_df.columns

if __name__ == "__main__":
    pytest.main(["-v", __file__])
