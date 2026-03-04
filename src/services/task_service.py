"""
Background Task Service
=======================
Celery-based asynchronous task execution:
- Background job processing
- Model training tasks
- Prediction tasks
- Data processing tasks
- Cleanup tasks
- Retry logic and error handling

Author: Production Team
Version: 1.0.0
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import Celery, Task
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from src.core.config import settings
from src.core.exceptions import ResourceNotFoundError, TaskExecutionError
from src.core.logging import get_logger

logger = get_logger(__name__)
celery_logger = get_task_logger(__name__)


# ============================================================================
# CELERY_CONFIGURATION
# ============================================================================

# Initialize Celery app
celery_app = Celery(
    "astrogeo_worker", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=86400,  # Results expire after 24 hours
    broker_connection_retry_on_startup=True,
)


# ============================================================================
# CUSTOM TASK BASE CLASS
# ============================================================================


class AstroGeoTask(Task):
    """
    Custom Celery task base class with error handling and logging.

    Features:
    - Automatic retry on failure
    - Structured logging
    - Error tracking
    - Performance monitoring
    """

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 5}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        celery_logger.error(
            f"Task {self.name} failed",
            extra={"task_id": task_id, "error": str(exc), "args": args, "kwargs": kwargs},
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        celery_logger.info(f"Task {self.name} completed", extra={"task_id": task_id})
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        celery_logger.warning(
            f"Task {self.name} retrying",
            extra={"task_id": task_id, "error": str(exc), "retries": self.request.retries},
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)


# ============================================================================
# MODEL TRAINING TASKS
# ============================================================================


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.train_model")
def train_model_task(
    self, model_id: str, dataset_id: str, hyperparameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Train ML model in background.

    Args:
        self: Task instance
        model_id: ML model ID
        dataset_id: Training dataset ID
        hyperparameters: Model hyperparameters

    Returns:
        dict: Training results

    Time complexity: O(n*m) where n=samples, m=features
    Space complexity: O(n*m)
    """
    celery_logger.info(
        "Starting model training", extra={"model_id": model_id, "dataset_id": dataset_id}
    )

    try:
        # Import training service
        from src.services.training_service import ModelTrainingService
        
        # Initialize training service
        training_service = ModelTrainingService()
        
        # Use dataset_id as the dataset path (assuming it's a file path or can be resolved)
        # In production, you might need to resolve dataset_id to actual file path
        dataset_path = f"data/datasets/{dataset_id}.csv"  # Adjust as needed
        
        # Extract training parameters
        model_type = hyperparameters.pop("model_type", "random_forest")
        target_column = hyperparameters.pop("target_column", "target")
        test_size = hyperparameters.pop("test_size", 0.2)
        cv_folds = hyperparameters.pop("cv_folds", 5)
        
        # Run async training in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            training_service.train_model(
                model_id=model_id,
                dataset_path=dataset_path,
                model_type=model_type,
                hyperparameters=hyperparameters,
                target_column=target_column,
                test_size=test_size,
                cv_folds=cv_folds
            )
        )
        
        loop.close()

        celery_logger.info(
            "Model training completed",
            extra={"model_id": model_id, "metrics": result.get("metrics", {})},
        )

        return result

    except Exception as e:
        celery_logger.error("Model training failed", extra={"error": str(e)})
        raise TaskExecutionError(
            agent_name="train_model", details={"model_id": model_id, "error": str(e)}
        )


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.evaluate_model")
def evaluate_model_task(self, model_id: str, test_dataset_id: str) -> Dict[str, Any]:
    """
    Evaluate model performance on test set.

    Args:
        self: Task instance
        model_id: ML model ID
        test_dataset_id: Test dataset ID

    Returns:
        dict: Evaluation metrics
    """
    celery_logger.info("Starting model evaluation", extra={"model_id": model_id})

    try:
        # Mock evaluation
        import time

        time.sleep(2)

        result = {
            "status": "completed",
            "model_id": model_id,
            "test_dataset_id": test_dataset_id,
            "metrics": {
                "accuracy": 0.94,
                "precision": 0.91,
                "recall": 0.90,
                "f1_score": 0.905,
                "auc_roc": 0.96,
            },
            "confusion_matrix": [[850, 50], [60, 840]],
            "evaluated_at": datetime.utcnow().isoformat(),
        }

        return result

    except Exception as e:
        celery_logger.error("Model evaluation failed", extra={"error": str(e)})
        raise TaskExecutionError(
            agent_name="evaluate_model", details={"model_id": model_id, "error": str(e)}
        )


# ============================================================================
# PREDICTION TASKS
# ============================================================================


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.batch_predict")
def batch_predict_task(
    self, model_id: str, input_data: List[Dict[str, Any]], batch_size: int = 100
) -> Dict[str, Any]:
    """
    Run batch predictions.

    Args:
        self: Task instance
        model_id: ML model ID
        input_data: List of input samples
        batch_size: Batch size for processing

    Returns:
        dict: Prediction results

    Time complexity: O(n) where n=number of samples
    Space complexity: O(n)
    """
    celery_logger.info(
        "Starting batch prediction", extra={"model_id": model_id, "num_samples": len(input_data)}
    )

    try:
        # Mock batch prediction
        predictions = []
        for i in range(0, len(input_data), batch_size):
            batch = input_data[i : i + batch_size]
            # Process batch
            batch_predictions = [
                {"input_id": item.get("id"), "prediction": 0.85, "confidence": 0.92}
                for item in batch
            ]
            predictions.extend(batch_predictions)

        result = {
            "status": "completed",
            "model_id": model_id,
            "total_predictions": len(predictions),
            "predictions": predictions,
            "completed_at": datetime.utcnow().isoformat(),
        }

        celery_logger.info(
            "Batch prediction completed", extra={"num_predictions": len(predictions)}
        )

        return result

    except Exception as e:
        celery_logger.error("Batch prediction failed", extra={"error": str(e)})
        raise TaskExecutionError(
            agent_name="batch_predict", details={"model_id": model_id, "error": str(e)}
        )


# ============================================================================
# DATA PROCESSING TASKS
# ============================================================================


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.process_dataset")
def process_dataset_task(self, dataset_id: str, processing_steps: List[str]) -> Dict[str, Any]:
    """
    Process dataset with specified transformations.

    Args:
        self: Task instance
        dataset_id: Dataset ID
        processing_steps: List of processing steps

    Returns:
            dict: Processing results
    """
    celery_logger.info(
        "Starting dataset processing", extra={"dataset_id": dataset_id, "steps": processing_steps}
    )

    try:
        # Mock processing
        import time

        time.sleep(3)

        result = {
            "status": "completed",
            "dataset_id": dataset_id,
            "steps_executed": processing_steps,
            "records_processed": 50000,
            "processing_time_seconds": 120,
            "output_path": f"/data/processed/{dataset_id}.parquet",
            "completed_at": datetime.utcnow().isoformat(),
        }

        return result

    except Exception as e:
        celery_logger.error("Dataset processing failed", extra={"error": str(e)})
        raise TaskExecutionError(
            agent_name="process_dataset", details={"dataset_id": dataset_id, "error": str(e)}
        )


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.extract_features")
def extract_features_task(self, dataset_id: str, feature_set: str) -> Dict[str, Any]:
    """
    Extract features from dataset.

    Args:
        self: Task instance
        dataset_id: Dataset ID
        feature_set: Feature set to extract

    Returns:
        dict: Extracted features
    """
    celery_logger.info(
        "Starting feature extraction", extra={"dataset_id": dataset_id, "feature_set": feature_set}
    )

    try:
        # Mock extraction
        import time

        time.sleep(4)

        result = {
            "status": "completed",
            "dataset_id": dataset_id,
            "feature_set": feature_set,
            "num_features": 125,
            "feature_names": [f"feature_{i}" for i in range(125)],
            "output_path": f"/data/features/{dataset_id}_{feature_set}.pkl",
            "completed_at": datetime.utcnow().isoformat(),
        }

        return result

    except Exception as e:
        celery_logger.error("Feature extraction failed", extra={"error": str(e)})
        raise TaskExecutionError(
            agent_name="extract_features", details={"dataset_id": dataset_id, "error": str(e)}
        )


# ============================================================================
# CLEANUP TASKS
# ============================================================================


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.cleanup_old_data")
def cleanup_old_data_task(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Cleanup old data and temporary files.

    Args:
        self: Task instance
        days_old: Delete data older than this many days

    Returns:
        dict: Cleanup results
    """
    celery_logger.info("Starting cleanup", extra={"days_old": days_old})

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Mock cleanup
        result = {
            "status": "completed",
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_predictions": 1500,
            "deleted_temp_files": 350,
            "freed_storage_mb": 5200,
            "completed_at": datetime.utcnow().isoformat(),
        }

        celery_logger.info(
            "Cleanup completed", extra={"deleted_items": result["deleted_predictions"]}
        )

        return result

    except Exception as e:
        celery_logger.error("Cleanup failed", extra={"error": str(e)})
        raise TaskExecutionError(agent_name="cleanup_old_data", details={"error": str(e)})


@celery_app.task(base=AstroGeoTask, bind=True, name="tasks.archive_old_models")
def archive_old_models_task(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Archive old unused models.

    Args:
        self: Task instance
        days_old: Archive models older than this many days

    Returns:
        dict: Archive results
    """
    celery_logger.info("Starting model archival", extra={"days_old": days_old})

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Mock archival
        result = {
            "status": "completed",
            "cutoff_date": cutoff_date.isoformat(),
            "models_archived": 25,
            "archive_path": "/data/archive/models",
            "completed_at": datetime.utcnow().isoformat(),
        }

        return result

    except Exception as e:
        celery_logger.error("Model archival failed", extra={"error": str(e)})
        raise TaskExecutionError(agent_name="archive_old_models", details={"error": str(e)})


# ============================================================================
# TASK MANAGEMENT SERVICE
# ============================================================================


class TaskService:
    """
    Service for managing background tasks.

    Features:
    - Submit tasks
    - Check task status
    - Cancel tasks
    - Retry failed tasks
    - Get task results
    """

    @staticmethod
    def submit_training_task(
        model_id: str, dataset_id: str, hyperparameters: Dict[str, Any]
    ) -> str:
        """
        Submit model training task.

        Args:
            model_id: ML model ID
            dataset_id: Training dataset ID
            hyperparameters: Model hyperparameters

        Returns:
            str: Task ID
        """
        task = train_model_task.delay(model_id, dataset_id, hyperparameters)
        logger.info("Submitted training task", extra={"task_id": task.id, "model_id": model_id})
        return str(task.id)

    @staticmethod
    def submit_prediction_task(
        model_id: str, input_data: List[Dict[str, Any]], batch_size: int = 100
    ) -> str:
        """
        Submit batch prediction task.

        Args:
            model_id: ML model ID
            input_data: Input samples
            batch_size: Batch size

        Returns:
            str: Task ID
        """
        task = batch_predict_task.delay(model_id, input_data, batch_size)
        logger.info(
            "Submitted prediction task", extra={"task_id": task.id, "num_samples": len(input_data)}
        )
        return str(task.id)

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            dict: Task status and result
        """
        task_result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "status": task_result.state,
            "result": task_result.result if task_result.successful() else None,
            "error": str(task_result.result) if task_result.failed() else None,
            "ready": task_result.ready(),
            "successful": task_result.successful(),
            "failed": task_result.failed(),
        }

    @staticmethod
    def cancel_task(task_id: str) -> bool:
        """
        Cancel running task.

        Args:
            task_id: Task ID

        Returns:
            bool: True if cancelled
        """
        task_result = AsyncResult(task_id, app=celery_app)
        task_result.revoke(terminate=True)

        logger.info("Task cancelled", extra={"task_id": task_id})
        return True

    @staticmethod
    def get_task_result(task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get task result (blocks until complete).

        Args:
            task_id: Task ID
            timeout: Maximum wait time in seconds

        Returns:
            Any: Task result

        Raises:
            TimeoutError: If task doesn't complete in time
        """
        task_result = AsyncResult(task_id, app=celery_app)
        return task_result.get(timeout=timeout)


# Export public API
__all__ = [
    "celery_app",
    "TaskService",
    "train_model_task",
    "batch_predict_task",
    "process_dataset_task",
    "extract_features_task",
    "cleanup_old_data_task",
    "archive_old_models_task",
]
