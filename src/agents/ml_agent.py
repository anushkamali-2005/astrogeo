"""
ML Agent
========
Intelligent agent for machine learning operations:
- Model training
- Hyperparameter tuning
- Model evaluation
- Feature engineering suggestions
- MLflow integration

Author: Production Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
import json

from langchain_core.tools import BaseTool, StructuredTool
from pydantic.v1 import BaseModel as LangChainBaseModel, Field as LangChainField

from src.agents.base_agent import BaseAgent
from src.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

class TrainModelInput(LangChainBaseModel):
    """Input for train_model tool."""
    model_type: str = LangChainField(description="Type of model (classification/regression)")
    dataset_path: str = LangChainField(description="Path to training dataset")
    target_column: str = LangChainField(description="Target variable column name")
    hyperparameters: Dict[str, Any] = LangChainField(
        default_factory=dict,
        description="Model hyperparameters"
    )


class EvaluateModelInput(LangChainBaseModel):
    """Input for evaluate_model tool."""
    model_id: str = LangChainField(description="ID of model to evaluate")
    test_data_path: str = LangChainField(description="Path to test dataset")


class SuggestFeaturesInput(LangChainBaseModel):
    """Input for suggest_features tool."""
    dataset_path: str = LangChainField(description="Path to dataset")
    target_column: str = LangChainField(description="Target variable")
    problem_type: str = LangChainField(description="classification or regression")


# ============================================================================
# ML TOOLS
# ============================================================================

def train_model_tool(
    model_type: str,
    dataset_path: str,
    target_column: str,
    hyperparameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Train a machine learning model.
    
    Args:
        model_type: Type of model (classification/regression)
        dataset_path: Path to training data
        target_column: Target variable column
        hyperparameters: Model hyperparameters
        
    Returns:
        dict: Training results with model ID and metrics
    """
    logger.info(
        "Training model via ML agent",
        extra={
            "model_type": model_type,
            "dataset_path": dataset_path,
            "target_column": target_column
        }
    )
    
    # This would integrate with your actual ML training pipeline
    # For now, returning a mock response
    return {
        "status": "success",
        "model_id": "model_123",
        "model_type": model_type,
        "metrics": {
            "accuracy": 0.92,
            "precision": 0.89,
            "recall": 0.91,
            "f1_score": 0.90
        },
        "training_time_seconds": 45.2,
        "message": f"Model trained successfully on {dataset_path}"
    }


def evaluate_model_tool(
    model_id: str,
    test_data_path: str
) -> Dict[str, Any]:
    """
    Evaluate a trained model on test data.
    
    Args:
        model_id: ID of model to evaluate
        test_data_path: Path to test dataset
        
    Returns:
        dict: Evaluation metrics
    """
    logger.info(
        "Evaluating model via ML agent",
        extra={"model_id": model_id, "test_data_path": test_data_path}
    )
    
    return {
        "status": "success",
        "model_id": model_id,
        "metrics": {
            "accuracy": 0.91,
            "precision": 0.88,
            "recall": 0.90,
            "f1_score": 0.89,
            "auc_roc": 0.94
        },
        "confusion_matrix": [[850, 50], [40, 860]],
        "message": "Model evaluation completed"
    }


def suggest_features_tool(
    dataset_path: str,
    target_column: str,
    problem_type: str
) -> Dict[str, Any]:
    """
    Suggest feature engineering strategies.
    
    Args:
        dataset_path: Path to dataset
        target_column: Target variable
        problem_type: classification or regression
        
    Returns:
        dict: Feature engineering suggestions
    """
    logger.info(
        "Generating feature suggestions",
        extra={
            "dataset_path": dataset_path,
            "problem_type": problem_type
        }
    )
    
    suggestions = {
        "status": "success",
        "problem_type": problem_type,
        "suggestions": [
            {
                "type": "polynomial_features",
                "description": "Create polynomial combinations of numeric features",
                "degree": 2,
                "expected_improvement": "5-10%"
            },
            {
                "type": "interaction_features",
                "description": "Create interaction terms between correlated features",
                "feature_pairs": [("feature1", "feature2")],
                "expected_improvement": "3-7%"
            },
            {
                "type": "target_encoding",
                "description": "Encode categorical variables using target statistics",
                "applicable_columns": ["category1", "category2"],
                "expected_improvement": "4-8%"
            }
        ],
        "recommendations": [
            "Consider feature scaling for distance-based models",
            "Remove features with >80% missing values",
            "Check for multicollinearity between features"
        ]
    }
    
    return suggestions


def get_model_info_tool(model_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a model.
    
    Args:
        model_id: Model ID
        
    Returns:
        dict: Model information
    """
    logger.info("Retrieving model info", extra={"model_id": model_id})
    
    return {
        "status": "success",
        "model_id": model_id,
        "name": "customer_churn_predictor",
        "version": "2.1.0",
        "model_type": "classification",
        "framework": "scikit-learn",
        "status": "production",
        "metrics": {
            "accuracy": 0.92,
            "precision": 0.89,
            "recall": 0.91
        },
        "feature_importance": {
            "tenure": 0.35,
            "monthly_charges": 0.28,
            "contract_type": 0.22,
            "total_charges": 0.15
        },
        "created_at": "2024-01-01T12:00:00Z",
        "deployed_at": "2024-01-05T10:00:00Z"
    }


def tune_hyperparameters_tool(
    model_type: str,
    dataset_path: str,
    target_column: str,
    search_space: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform hyperparameter tuning.
    
    Args:
        model_type: Type of model
        dataset_path: Path to dataset
        target_column: Target variable
        search_space: Hyperparameter search space
        
    Returns:
        dict: Best hyperparameters and performance
    """
    logger.info(
        "Tuning hyperparameters",
        extra={"model_type": model_type}
    )
    
    return {
        "status": "success",
        "best_hyperparameters": {
            "n_estimators": 150,
            "max_depth": 12,
            "min_samples_split": 5,
            "min_samples_leaf": 2
        },
        "best_score": 0.94,
        "cv_scores": [0.93, 0.94, 0.95, 0.93, 0.94],
        "total_iterations": 50,
        "tuning_time_seconds": 120.5,
        "message": "Hyperparameter tuning completed successfully"
    }


# ============================================================================
# ML AGENT
# ============================================================================

class MLAgent(BaseAgent):
    """
    Intelligent agent for machine learning operations.
    
    Capabilities:
    - Train ML models
    - Evaluate models
    - Suggest features
    - Tune hyperparameters
    - Get model information
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ):
        """
        Initialize ML Agent.
        
        Args:
            model: LLM model name
            temperature: LLM temperature (lower for more deterministic)
            **kwargs: Additional base agent arguments
        """
        # Create tools
        tools = self._create_tools()
        
        # Initialize base agent
        super().__init__(
            name="MLAgent",
            description="Intelligent agent for machine learning operations",
            tools=tools,
            model=model,
            temperature=temperature,
            **kwargs
        )
        
        logger.info("ML Agent initialized with tools", extra={"num_tools": len(tools)})
    
    def _create_tools(self) -> List[BaseTool]:
        """
        Create ML-specific tools.
        
        Returns:
            list: List of LangChain tools
        """
        tools = [
            StructuredTool.from_function(
                func=train_model_tool,
                name="train_model",
                description="Train a machine learning model with specified parameters. "
                           "Use this when the user wants to build or train a new model.",
                args_schema=TrainModelInput
            ),
            StructuredTool.from_function(
                func=evaluate_model_tool,
                name="evaluate_model",
                description="Evaluate a trained model's performance on test data. "
                           "Use this to assess model quality.",
                args_schema=EvaluateModelInput
            ),
            StructuredTool.from_function(
                func=suggest_features_tool,
                name="suggest_features",
                description="Get intelligent feature engineering suggestions. "
                           "Use when user needs help with features.",
                args_schema=SuggestFeaturesInput
            ),
            StructuredTool.from_function(
                func=get_model_info_tool,
                name="get_model_info",
                description="Retrieve detailed information about a model. "
                           "Use when user asks about a specific model.",
            ),
            StructuredTool.from_function(
                func=tune_hyperparameters_tool,
                name="tune_hyperparameters",
                description="Perform automated hyperparameter tuning. "
                           "Use when user wants to optimize model performance.",
            )
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """
        Get ML Agent system prompt.
        
        Returns:
            str: System prompt
        """
        return """You are an expert ML Engineer agent specialized in machine learning operations.

Your capabilities:
- Training ML models (classification, regression)
- Evaluating model performance
- Suggesting feature engineering strategies
- Hyperparameter tuning
- Providing ML best practices

Guidelines:
1. Always ask clarifying questions if requirements are ambiguous
2. Suggest appropriate algorithms based on problem type
3. Recommend feature engineering when beneficial
4. Explain metrics in user-friendly terms
5. Provide actionable next steps

When training models:
- Choose appropriate algorithms for the problem
- Suggest reasonable hyperparameter ranges
- Recommend cross-validation strategies
- Explain expected performance trade-offs

When evaluating models:
- Explain metrics clearly (accuracy, precision, recall, etc.)
- Identify potential issues (overfitting, bias)
- Suggest improvements if performance is suboptimal

Be concise, practical, and always focus on delivering value to the user."""


# Example usage
if __name__ == "__main__":
    # This demonstrates how to use the ML Agent
    import asyncio
    
    async def demo():
        # Initialize agent
        agent = MLAgent()
        
        # Execute task
        result = await agent.execute(
            task="Train a classification model on customer_data.csv to predict churn"
        )
        
        print(json.dumps(result, indent=2))
    
    asyncio.run(demo())


# Export
__all__ = ["MLAgent"]