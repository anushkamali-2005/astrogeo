"""
Predictions Routes
=================
API endpoints for ML model predictions.

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.connection import get_db
from src.schemas.requests import PredictionRequest, BatchPredictionRequest
from src.schemas.responses import (
    PredictionResponse,
    BatchPredictionResponse,
    SuccessResponse
)
from src.services.prediction_service import prediction_service
from src.core.security import get_current_user


logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/predict",
    response_model=SuccessResponse[PredictionResponse],
    status_code=status.HTTP_200_OK,
    summary="Make prediction",
    description="Get ML model prediction for input features"
)
async def predict(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SuccessResponse[PredictionResponse]:
    """
    Make single prediction.
    
    Args:
        request: Prediction request with features
        db: Database session
        current_user: Authenticated user
        
    Returns:
        SuccessResponse: Prediction result
        
    Example:
        ```json
        {
            "model_name": "churn_predictor",
            "features": {
                "tenure": 24,
                "monthly_charges": 79.99,
                "contract_type": "two_year"
            },
            "return_probabilities": true
        }
        ```
    """
    try:
        user_id = current_user.get("sub")  # User ID from JWT
        
        logger.info(
            "Prediction request received",
            extra={
                "user_id": user_id,
                "model_name": request.model_name,
                "model_id": str(request.model_id) if request.model_id else None
            }
        )
        
        # Make prediction
        result = await prediction_service.predict(
            db=db,
            request=request,
            user_id=UUID(user_id) if user_id else None
        )
        
        return SuccessResponse(
            data=result,
            message="Prediction completed successfully"
        )
    
    except Exception as e:
        logger.error("Prediction endpoint error", error=e)
        raise


@router.post(
    "/predict/batch",
    response_model=SuccessResponse[BatchPredictionResponse],
    status_code=status.HTTP_200_OK,
    summary="Batch predictions",
    description="Get predictions for multiple inputs"
)
async def batch_predict(
    request: BatchPredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SuccessResponse[BatchPredictionResponse]:
    """
    Make batch predictions.
    
    Args:
        request: Batch prediction request
        db: Database session
        current_user: Authenticated user
        
    Returns:
        SuccessResponse: Batch prediction results
        
    Example:
        ```json
        {
            "model_name": "churn_predictor",
            "features_list": [
                {"tenure": 24, "monthly_charges": 79.99},
                {"tenure": 12, "monthly_charges": 59.99}
            ],
            "return_probabilities": true
        }
        ```
    """
    try:
        user_id = current_user.get("sub")
        
        logger.info(
            "Batch prediction request received",
            extra={
                "user_id": user_id,
                "batch_size": len(request.features_list),
                "model_name": request.model_name
            }
        )
        
        # Validate batch size
        if len(request.features_list) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size exceeds maximum of 1000"
            )
        
        # Make predictions
        result = await prediction_service.batch_predict(
            db=db,
            request=request,
            user_id=UUID(user_id) if user_id else None
        )
        
        return SuccessResponse(
            data=result,
            message=f"Batch prediction completed: {result.successful_count}/{result.total_count} successful"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch prediction endpoint error", error=e)
        raise


@router.get(
    "/predictions/{prediction_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get prediction",
    description="Retrieve prediction by ID"
)
async def get_prediction(
    prediction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get prediction details.
    
    Args:
        prediction_id: Prediction ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        SuccessResponse: Prediction details
    """
    try:
        from sqlalchemy import select
        from src.database.models import Prediction
        
        # Get prediction
        result = await db.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        prediction = result.scalar_one_or_none()
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found"
            )
        
        # Check ownership (optional - implement based on requirements)
        # user_id = current_user.get("sub")
        # if prediction.user_id and str(prediction.user_id) != user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        return SuccessResponse(
            data={
                "id": str(prediction.id),
                "model_id": str(prediction.model_id),
                "input_data": prediction.input_data,
                "output_data": prediction.output_data,
                "confidence": prediction.confidence,
                "execution_time_ms": prediction.execution_time_ms,
                "created_at": prediction.created_at.isoformat(),
                "feedback_score": prediction.feedback_score,
                "feedback_comment": prediction.feedback_comment
            },
            message="Prediction retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get prediction error", error=e)
        raise


@router.post(
    "/predictions/{prediction_id}/feedback",
    response_model=SuccessResponse[Dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Submit feedback",
    description="Submit feedback for a prediction"
)
async def submit_feedback(
    prediction_id: UUID,
    feedback_score: int,
    feedback_comment: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SuccessResponse[Dict[str, str]]:
    """
    Submit prediction feedback.
    
    Args:
        prediction_id: Prediction ID
        feedback_score: Score (1-5)
        feedback_comment: Optional comment
        db: Database session
        current_user: Authenticated user
        
    Returns:
        SuccessResponse: Confirmation message
    """
    try:
        from sqlalchemy import select
        from src.database.models import Prediction
        
        # Validate score
        if not 1 <= feedback_score <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback score must be between 1 and 5"
            )
        
        # Get prediction
        result = await db.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        prediction = result.scalar_one_or_none()
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found"
            )
        
        # Update feedback
        prediction.feedback_score = feedback_score
        prediction.feedback_comment = feedback_comment
        
        await db.commit()
        
        logger.info(
            "Feedback submitted",
            extra={
                "prediction_id": str(prediction_id),
                "score": feedback_score
            }
        )
        
        return SuccessResponse(
            data={"message": "Feedback submitted successfully"},
            message="Thank you for your feedback"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Submit feedback error", error=e)
        raise


@router.get(
    "/predictions/user/history",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="User prediction history",
    description="Get user's prediction history"
)
async def get_user_predictions(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get user prediction history.
    
    Args:
        limit: Number of results
        offset: Pagination offset
        db: Database session
        current_user: Authenticated user
        
    Returns:
        SuccessResponse: User predictions
    """
    try:
        from sqlalchemy import select, func
        from src.database.models import Prediction
        
        user_id = UUID(current_user.get("sub"))
        
        # Get total count
        count_result = await db.execute(
            select(func.count(Prediction.id))
            .where(Prediction.user_id == user_id)
        )
        total = count_result.scalar()
        
        # Get predictions
        result = await db.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        predictions = result.scalars().all()
        
        return SuccessResponse(
            data={
                "predictions": [
                    {
                        "id": str(p.id),
                        "model_id": str(p.model_id),
                        "prediction": p.output_data.get("prediction"),
                        "confidence": p.confidence,
                        "created_at": p.created_at.isoformat()
                    }
                    for p in predictions
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            },
            message=f"Retrieved {len(predictions)} predictions"
        )
    
    except Exception as e:
        logger.error("Get user predictions error", error=e)
        raise


__all__ = ["router"]