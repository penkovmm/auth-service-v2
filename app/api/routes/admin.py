"""
Admin routes for managing whitelist and users.

Protected with HTTP Basic Auth.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_admin
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import AdminService
from app.schemas import (
    WhitelistResponse,
    AllowedUserResponse,
    AddToWhitelistRequest,
    RemoveFromWhitelistRequest,
    UserListResponse,
    UserResponse,
    AuditLogListResponse,
    StatisticsResponse,
    SuccessResponse,
    MessageResponse,
)
from app.utils.exceptions import ValidationError

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/whitelist", response_model=AllowedUserResponse)
async def add_to_whitelist(
    request_data: AddToWhitelistRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Add user to whitelist.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Request Body:**
    - hh_user_id: HeadHunter user ID
    - description: Optional description

    **Returns:**
    - Whitelist entry details

    **Errors:**
    - 400: Invalid request data
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        allowed_user = await admin_service.add_to_whitelist(
            hh_user_id=request_data.hh_user_id,
            description=request_data.description,
            added_by=admin[0],  # admin username
        )

        await db.commit()

        logger.info(
            "user_added_to_whitelist_via_api",
            hh_user_id=request_data.hh_user_id,
            admin=admin[0],
        )

        return AllowedUserResponse.model_validate(allowed_user)

    except ValidationError as e:
        logger.warning("whitelist_add_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            "whitelist_add_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to whitelist: {str(e)}",
        )


@router.delete("/whitelist", response_model=MessageResponse)
async def remove_from_whitelist(
    request_data: RemoveFromWhitelistRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Remove user from whitelist.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Request Body:**
    - hh_user_id: HeadHunter user ID

    **Returns:**
    - Success message

    **Errors:**
    - 404: User not found in whitelist
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        removed = await admin_service.remove_from_whitelist(
            hh_user_id=request_data.hh_user_id
        )

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request_data.hh_user_id} not found in whitelist",
            )

        await db.commit()

        logger.info(
            "user_removed_from_whitelist_via_api",
            hh_user_id=request_data.hh_user_id,
            admin=admin[0],
        )

        return MessageResponse(
            message=f"User {request_data.hh_user_id} removed from whitelist"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "whitelist_remove_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from whitelist: {str(e)}",
        )


@router.get("/whitelist", response_model=WhitelistResponse)
async def get_whitelist(
    active_only: bool = True,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Get whitelist.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Query Parameters:**
    - active_only: Return only active users (default: true)
    - limit: Maximum number of entries to return

    **Returns:**
    - List of whitelist entries
    - Total count

    **Errors:**
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        allowed_users = await admin_service.get_whitelist(
            active_only=active_only,
            limit=limit,
        )

        logger.debug("whitelist_retrieved_via_api", count=len(allowed_users))

        return WhitelistResponse(
            allowed_users=[
                AllowedUserResponse.model_validate(u) for u in allowed_users
            ],
            total=len(allowed_users),
        )

    except Exception as e:
        logger.error(
            "whitelist_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve whitelist: {str(e)}",
        )


@router.get("/users", response_model=UserListResponse)
async def get_users(
    active_only: bool = False,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Get all users.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Query Parameters:**
    - active_only: Return only active users (default: false)
    - limit: Maximum number of users to return

    **Returns:**
    - List of users
    - Total count

    **Errors:**
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        users = await admin_service.get_all_users(
            active_only=active_only,
            limit=limit,
        )

        logger.debug("users_retrieved_via_api", count=len(users))

        return UserListResponse(
            users=[UserResponse.model_validate(u) for u in users],
            total=len(users),
        )

    except Exception as e:
        logger.error(
            "users_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}",
        )


@router.get("/users/{user_id}/audit", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    user_id: int,
    limit: int = 100,
    event_category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Get audit logs for a user.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Path Parameters:**
    - user_id: User ID

    **Query Parameters:**
    - limit: Maximum number of logs (default: 100)
    - event_category: Filter by category (auth, admin, security)

    **Returns:**
    - List of audit logs
    - Total count

    **Errors:**
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        logs = await admin_service.get_user_audit_logs(
            user_id=user_id,
            limit=limit,
            event_category=event_category,
        )

        logger.debug("user_audit_logs_retrieved_via_api", user_id=user_id, count=len(logs))

        from app.schemas.responses import AuditLogResponse

        return AuditLogListResponse(
            logs=[AuditLogResponse.model_validate(log) for log in logs],
            total=len(logs),
        )

    except Exception as e:
        logger.error(
            "audit_logs_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}",
        )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    admin: tuple[str, str] = Depends(verify_admin),
):
    """
    Get system statistics.

    **Authentication:** HTTP Basic Auth (admin credentials required)

    **Returns:**
    - total_users: Total number of users
    - active_users: Number of active users
    - whitelisted_users: Number of active whitelist entries
    - total_whitelist_entries: Total whitelist entries

    **Errors:**
    - 401: Unauthorized
    - 500: Internal server error
    """
    admin_service = AdminService(db)

    try:
        stats = await admin_service.get_statistics()

        logger.debug("statistics_retrieved_via_api", **stats)

        return StatisticsResponse(**stats)

    except Exception as e:
        logger.error(
            "statistics_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}",
        )
