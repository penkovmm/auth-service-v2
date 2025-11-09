"""
Main FastAPI application.

Entry point for the HH Auth Service v2.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import close_db
from app.api.routes import oauth_router, admin_router, health_router
from app.utils.exceptions import (
    AuthServiceException,
    OAuthError,
    TokenError,
    SessionError,
    UserError,
)

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await close_db()
    logger.info("application_shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="OAuth 2.0 Authentication Service for HeadHunter API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# === Exception Handlers ===


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request data",
            "details": exc.errors(),
        },
    )


@app.exception_handler(OAuthError)
async def oauth_exception_handler(request: Request, exc: OAuthError):
    """Handle OAuth-related errors."""
    logger.warning(
        "oauth_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "OAuthError",
            "message": str(exc),
        },
    )


@app.exception_handler(TokenError)
async def token_exception_handler(request: Request, exc: TokenError):
    """Handle token-related errors."""
    logger.warning(
        "token_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "TokenError",
            "message": str(exc),
        },
    )


@app.exception_handler(SessionError)
async def session_exception_handler(request: Request, exc: SessionError):
    """Handle session-related errors."""
    logger.warning(
        "session_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "SessionError",
            "message": str(exc),
        },
    )


@app.exception_handler(UserError)
async def user_exception_handler(request: Request, exc: UserError):
    """Handle user-related errors."""
    logger.warning(
        "user_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "UserError",
            "message": str(exc),
        },
    )


@app.exception_handler(AuthServiceException)
async def auth_service_exception_handler(request: Request, exc: AuthServiceException):
    """Handle generic auth service errors."""
    logger.error(
        "auth_service_error",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(
        "unexpected_error",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


# === Middleware ===


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    response = await call_next(request)

    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )

    return response


# === Include Routers ===

app.include_router(health_router)
app.include_router(oauth_router)
app.include_router(admin_router)


# === Root Endpoint ===


@app.get("/")
async def root():
    """
    Root endpoint.

    Redirects to the main web UI (parser.penkovmm.ru).
    Users should access the application through parser.penkovmm.ru.
    This service is for OAuth callbacks only.
    """
    return RedirectResponse(url="https://parser.penkovmm.ru", status_code=302)
