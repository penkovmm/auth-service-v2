"""
Health check and system routes.

Provides endpoints for monitoring service health.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas import HealthCheckResponse

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Checks:
    - Service is running
    - Database connection

    **Returns:**
    - status: healthy, degraded, or unhealthy
    - version: Application version
    - environment: Current environment
    - database: Database connection status
    - timestamp: Current timestamp

    **Status codes:**
    - 200: Service is healthy
    - 503: Service is unhealthy (database down)
    """
    settings = get_settings()
    db_status = "disconnected"
    overall_status = "unhealthy"

    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        if result:
            db_status = "connected"
            overall_status = "healthy"
    except Exception as e:
        logger.error("health_check_db_error", error=str(e))
        db_status = "disconnected"
        overall_status = "unhealthy"

    health_response = HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )

    if overall_status != "healthy":
        from fastapi import Response

        # Return 503 if unhealthy but still return data
        return Response(
            content=health_response.model_dump_json(),
            media_type="application/json",
            status_code=503,
        )

    return health_response


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint.

    **Returns:**
    - pong

    Used for basic availability checks.
    """
    return {"ping": "pong"}
