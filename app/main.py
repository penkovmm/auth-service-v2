"""
Main FastAPI application.

Entry point for the HH Auth Service v2.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Cookie, Depends
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import close_db, get_db
from app.api.routes import oauth_router, admin_router, health_router
from app.services import SessionService
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


@app.get("/", response_class=HTMLResponse)
async def root(
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Root endpoint - main entry point for users.

    Checks if user has valid session:
    - If yes: redirects to parser.penkovmm.ru
    - If no: shows login page
    """
    # Check if user has valid session
    if session_id:
        try:
            session_service = SessionService(db)
            user_session = await session_service.get_session(session_id)

            if user_session and user_session.is_valid:
                # User has valid session, redirect to parser
                return RedirectResponse(url="https://parser.penkovmm.ru", status_code=302)
        except Exception as e:
            logger.warning(f"Session validation failed: {e}")

    # No valid session - show login page
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход - HH Resume Parser</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 500px;
                width: 100%;
                padding: 40px;
                text-align: center;
            }

            .logo {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 30px;
                font-size: 40px;
            }

            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
                font-weight: 600;
            }

            .subtitle {
                color: #666;
                margin-bottom: 40px;
                font-size: 16px;
                line-height: 1.6;
            }

            .login-button {
                background: #D6001C;
                color: white;
                border: none;
                padding: 16px 40px;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                box-shadow: 0 4px 12px rgba(214, 0, 28, 0.3);
            }

            .login-button:hover {
                background: #B8001A;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(214, 0, 28, 0.4);
            }

            .login-button:active {
                transform: translateY(0);
            }

            .footer {
                margin-top: 40px;
                color: #999;
                font-size: 14px;
            }

            .loading {
                display: none;
                margin-top: 20px;
                color: #667eea;
                font-size: 14px;
            }

            .loading.active {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">👔</div>
            <h1>HH Resume Parser</h1>
            <p class="subtitle">
                Для доступа к системе подбора резюме войдите через свой аккаунт HeadHunter
            </p>
            <button class="login-button" onclick="startLogin()">
                Войти через hh.ru
            </button>
            <div class="loading" id="loading">
                Перенаправление на HeadHunter...
            </div>
            <div class="footer">
                © 2025 Корпоративный университет АО «Газстройпром»
            </div>
        </div>

        <script>
            async function startLogin() {
                const loadingEl = document.getElementById('loading');
                loadingEl.classList.add('active');

                try {
                    // Get authorization URL from auth service
                    const response = await fetch('/auth/login');
                    const data = await response.json();

                    if (data.authorization_url) {
                        // Redirect to HeadHunter OAuth
                        window.location.href = data.authorization_url;
                    } else {
                        throw new Error('No authorization URL received');
                    }
                } catch (error) {
                    console.error('Login failed:', error);
                    loadingEl.classList.remove('active');
                    alert('Ошибка при входе. Попробуйте еще раз.');
                }
            }
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
