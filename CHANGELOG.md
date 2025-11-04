# Changelog

All notable changes to Auth Service v2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-04

### Added
- Complete OAuth 2.0 flow with HeadHunter API
- Automatic token refresh functionality
- Session-based authentication system
- Whitelist-based access control
- Encrypted token storage using Fernet (AES-128)
- Admin API with HTTP Basic Authentication
- Comprehensive audit logging
- Health check and Prometheus metrics endpoints
- Rate limiting (100 req/min per IP)
- Async/await architecture for high performance
- Docker and Docker Compose support
- Database migrations with Alembic
- Structured logging with sensitive data filtering
- 21 security tests with 100% pass rate
- Comprehensive documentation suite:
  - OAuth flow documentation with examples
  - API usage examples (Python, JavaScript, Django, Flask, FastAPI)
  - Administrator guide
  - Architecture documentation
  - Production deployment checklist

### Technical Stack
- Python 3.12
- FastAPI 0.104+
- PostgreSQL 17
- SQLAlchemy 2.0 (async)
- Docker & Docker Compose
- Uvicorn (ASGI server)

### Security Features
- Fernet encryption for tokens (AES-128-CBC + HMAC)
- bcrypt password hashing (work factor 12)
- CSRF protection via OAuth state validation
- Whitelist-based authorization
- Sensitive data filtering in logs
- Session expiration (configurable, default 30 days)
- Audit logging of all critical events
- Non-root container user

### API Endpoints
#### OAuth Flow
- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/exchange` - Exchange code for session
- `POST /auth/token` - Get HH access token
- `POST /auth/refresh` - Force token refresh
- `POST /auth/logout` - Terminate session

#### Users
- `GET /users/me` - Get current user info

#### Admin (Basic Auth required)
- `POST /admin/users/allow` - Add user to whitelist
- `DELETE /admin/users/{hh_user_id}` - Remove from whitelist
- `GET /admin/users` - List allowed users
- `GET /admin/sessions` - View active sessions
- `DELETE /admin/sessions/{session_id}` - Terminate session
- `GET /admin/audit-log` - View audit log

#### Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Database Schema
- `users` - HH user information
- `user_sessions` - Active sessions with expiration
- `oauth_tokens` - Encrypted access/refresh tokens
- `oauth_states` - CSRF protection tokens
- `oauth_exchange_codes` - Temporary authorization codes
- `allowed_users` - Whitelist
- `audit_log` - Event logging

### Documentation
- README with quick start guide
- OAuth 2.0 flow documentation with sequence diagrams
- Complete API examples in multiple languages
- Administrator guide with operational procedures
- Architecture documentation with system diagrams
- Production deployment checklist (100+ items)

## [1.0.0] - Initial Development

### Note
Version 1.0 was the initial prototype. Version 2.0 is a complete rewrite with:
- Modern async architecture
- Enhanced security
- Comprehensive documentation
- Production-ready Docker deployment
- Complete test coverage
