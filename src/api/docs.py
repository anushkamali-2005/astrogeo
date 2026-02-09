"""
API Documentation Enhancement
==============================
Enhanced OpenAPI/Swagger documentation with examples.

Author: Production Team
Version: 1.0.0
"""

from typing import Any, Dict

# ============================================================================
# API METADATA
# ============================================================================

API_TITLE = "AstroGeo AI MLOps Platform API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## AstroGeo AI MLOps Platform

Production-grade geospatial AI platform with advanced astronomical analysis capabilities.

### Features

* 🤖 **AI Agents** - Data, ML, Geo, and Astronomical agents with specialized tools
* 🗺️ **Geospatial Analytics** - PostGIS-powered spatial queries and GeoJSON support
* 🔐 **Authentication** - JWT-based secure authentication with refresh tokens
* 📊 **ML Pipeline** - Complete model training, evaluation, and deployment workflow
* 🚀 **Background Tasks** - Celery-based async task processing
* 📧 **Notifications** - Email notifications for model training and alerts
* 📈 **Monitoring** - Health checks and metrics collection

### Authentication

Most endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Rate Limiting

- Login/Register: 5 requests per minute
- Password Reset: 3 requests per 5 minutes
- API calls: 100 requests per minute per user
"""

API_TAGS_METADATA = [
    {"name": "Authentication", "description": "User registration, login, and token management"},
    {"name": "Locations", "description": "Geospatial location management with PostGIS"},
    {"name": "Predictions", "description": "ML model predictions and batch processing"},
    {"name": "Agents", "description": "AI agent execution and orchestration"},
    {"name": "Models", "description": "ML model training, evaluation, and deployment"},
    {"name": "Admin", "description": "Administrative operations (admin only)"},
    {"name": "Health", "description": "System health and monitoring endpoints"},
]


# ============================================================================
# EXAMPLE RESPONSES
# ============================================================================

EXAMPLES = {
    "user_registration": {
        "request": {
            "email": "user@example.com",
            "username": "johndoe",
            "password": "SecurePass123!",
            "full_name": "John Doe",
        },
        "response": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "username": "johndoe",
            "full_name": "John Doe",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
        },
    },
    "login": {
        "request": {"email": "user@example.com", "password": "SecurePass123!"},
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
        },
    },
    "location_create": {
        "request": {
            "name": "Observatory Site",
            "description": "Primary observation location",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "elevation": 100.5,
            "location_type": "observatory",
        },
        "response": {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Observatory Site",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "geometry": {"type": "Point", "coordinates": [-118.2437, 34.0522]},
            "created_at": "2024-01-01T00:00:00Z",
        },
    },
    "prediction": {
        "request": {
            "model_id": "550e8400-e29b-41d4-a716-446655440002",
            "input_data": {"feature_1": 10.5, "feature_2": 25.3, "feature_3": "category_a"},
        },
        "response": {
            "prediction": 0.85,
            "confidence": 0.92,
            "model_version": "1.2.0",
            "prediction_time_ms": 15,
        },
    },
    "agent_execution": {
        "request": {
            "agent_type": "astro",
            "task": "Calculate the distance to Mars tonight",
            "parameters": {"observer_location": "New York"},
        },
        "response": {
            "execution_id": "770e8400-e29b-41d4-a716-446655440003",
            "status": "completed",
            "result": {
                "distance_au": 1.52,
                "distance_km": 227400000,
                "calculation_time": "2024-01-01T00:00:00Z",
            },
            "duration_seconds": 2.5,
        },
    },
}


# ============================================================================
# ERROR RESPONSES
# ============================================================================

ERROR_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid input data",
                        "details": {"field": "email", "issue": "Invalid email format"},
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": {"code": "AUTHENTICATION_ERROR", "message": "Invalid or expired token"}
                }
            }
        },
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": {"code": "AUTHORIZATION_ERROR", "message": "Insufficient permissions"}
                }
            }
        },
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RECORD_NOT_FOUND",
                        "message": "Resource not found",
                        "details": {
                            "resource_type": "Location",
                            "resource_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    }
                }
            }
        },
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "details": {"retry_after_seconds": 60},
                    }
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                    }
                }
            }
        },
    },
}


# Export
__all__ = [
    "API_TITLE",
    "API_VERSION",
    "API_DESCRIPTION",
    "API_TAGS_METADATA",
    "EXAMPLES",
    "ERROR_RESPONSES",
]
