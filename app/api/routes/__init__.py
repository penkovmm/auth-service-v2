"""
API routes package.

All API route modules.
"""

from app.api.routes.oauth import router as oauth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.health import router as health_router

__all__ = [
    "oauth_router",
    "admin_router",
    "health_router",
]
