"""
AstroGeo Data Ingestion
========================
Multi-format data loading and saving utilities.
Supports CSV, Parquet, Excel, and JSON formats.

Author: Production Team
Version: 1.0.0
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Supported file extensions and their loaders
_LOADERS = {
    ".csv": pd.read_csv,
    ".tsv": lambda p, **kw: pd.read_csv(p, sep="\t", **kw),
    ".parquet": pd.read_parquet,
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
    ".json": pd.read_json,
    ".jsonl": lambda p, **kw: pd.read_json(p, lines=True, **kw),
    ".feather": pd.read_feather,
}

_SAVERS = {
    ".csv": lambda df, p, **kw: df.to_csv(p, index=False, **kw),
    ".tsv": lambda df, p, **kw: df.to_csv(p, sep="\t", index=False, **kw),
    ".parquet": lambda df, p, **kw: df.to_parquet(p, index=False, **kw),
    ".xlsx": lambda df, p, **kw: df.to_excel(p, index=False, **kw),
    ".json": lambda df, p, **kw: df.to_json(p, orient="records", indent=2, **kw),
    ".jsonl": lambda df, p, **kw: df.to_json(p, orient="records", lines=True, **kw),
    ".feather": lambda df, p, **kw: df.to_feather(p, **kw),
}


def load_dataset(path: str, **kwargs: Any) -> pd.DataFrame:
    """
    Load CSV, Parquet, Excel, JSON, or Feather file into DataFrame.

    Args:
        path: File path to load from.
        **kwargs: Additional keyword arguments passed to the pandas reader.

    Returns:
        pd.DataFrame: Loaded data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file extension is unsupported.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    suffix = filepath.suffix.lower()
    loader = _LOADERS.get(suffix)

    if loader is None:
        supported = ", ".join(_LOADERS.keys())
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported: {supported}"
        )

    df = loader(filepath, **kwargs)
    logger.info(f"Loaded dataset from {path}: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def save_dataset(df: pd.DataFrame, path: str, **kwargs: Any) -> None:
    """
    Save DataFrame to appropriate format based on file extension.

    Args:
        df: DataFrame to save.
        path: Output file path (extension determines format).
        **kwargs: Additional keyword arguments passed to the pandas writer.
    """
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    suffix = filepath.suffix.lower()
    saver = _SAVERS.get(suffix)

    if saver is None:
        supported = ", ".join(_SAVERS.keys())
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported: {supported}"
        )

    saver(df, filepath, **kwargs)
    logger.info(f"Saved dataset to {path}: {df.shape[0]} rows × {df.shape[1]} cols")


def get_dataset_info(path: str) -> Dict[str, Any]:
    """
    Get metadata about a dataset without loading it fully.

    Args:
        path: File path to inspect.

    Returns:
        Dict with file metadata.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    info = {
        "path": str(filepath.resolve()),
        "name": filepath.name,
        "format": filepath.suffix.lower(),
        "size_bytes": filepath.stat().st_size,
        "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
    }

    # Quick preview
    try:
        if filepath.suffix.lower() == ".csv":
            preview = pd.read_csv(filepath, nrows=5)
        elif filepath.suffix.lower() == ".parquet":
            preview = pd.read_parquet(filepath).head(5)
        else:
            preview = load_dataset(str(filepath)).head(5)

        info["columns"] = list(preview.columns)
        info["dtypes"] = {col: str(dtype) for col, dtype in preview.dtypes.items()}
        info["n_columns"] = len(preview.columns)
    except Exception as e:
        info["preview_error"] = str(e)

    return info


__all__ = ["load_dataset", "save_dataset", "get_dataset_info"]
