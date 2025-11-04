# Architecture Documentation

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Technology Stack](#technology-stack)

## System Overview

Auth Service v2 is a standalone microservice that handles OAuth 2.0 authentication with HeadHunter API. It provides secure token storage, automatic token refresh, and session management for client applications.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client Applications                              │
│  (Web Apps, Mobile Apps, Backend Services, Scripts)                    │
└────────────┬────────────────────────────────────┬────────────────────────┘
             │                                    │
             │ REST API                           │ Admin API
             │                                    │ (Basic Auth)
             │                                    │
┌────────────▼────────────────────────────────────▼────────────────────────┐
│                        Auth Service v2                                   │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐│
│  │   FastAPI    │  │   Services   │  │ Repositories │  │   Models    ││
│  │   Routes     │─>│   Layer      │─>│   Layer      │─>│  (SQLAlch.) ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘│
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  Security    │  │   Logging    │  │    Config    │                 │
│  │  (Fernet)    │  │ (structlog)  │  │  (Pydantic)  │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└────────────┬──────────────────────────────┬──────────────────────────────┘
             │                              │
             │                              │ OAuth 2.0
             │                              ▼
             │                    ┌──────────────────────┐
             │                    │   HeadHunter API     │
             │                    │  (api.hh.ru)         │
             │                    └──────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                              │
│  (Users, Sessions, Tokens, Whitelist, Audit Logs)                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API Layer (FastAPI)                        │
│                                                                     │
│  /auth/*        /admin/*        /users/*        /health  /metrics  │
│  (OAuth)        (Admin)         (User Info)                        │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ Depends on
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Service Layer                              │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ HHOAuthService   │  │ SessionService   │  │  TokenService    │ │
│  │                  │  │                  │  │                  │ │
│  │ - authorize()    │  │ - create()       │  │ - save()         │ │
│  │ - callback()     │  │ - validate()     │  │ - get_active()   │ │
│  │ - get_token()    │  │ - terminate()    │  │ - refresh()      │ │
│  │ - refresh()      │  │ - cleanup()      │  │ - revoke()       │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │  AdminService    │                                              │
│  │                  │                                              │
│  │ - manage_users() │                                              │
│  │ - view_sessions()│                                              │
│  │ - audit_logs()   │                                              │
│  └──────────────────┘                                              │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ Uses
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Repository Layer                              │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐│
│  │   User      │  │  Session    │  │   Token     │  │  Audit    ││
│  │ Repository  │  │ Repository  │  │ Repository  │  │Repository ││
│  │             │  │             │  │             │  │           ││
│  │ - CRUD ops  │  │ - CRUD ops  │  │ - CRUD ops  │  │ - CRUD    ││
│  │ - queries   │  │ - queries   │  │ - queries   │  │ - queries ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘│
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ Operates on
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Database Models (SQLAlchemy)                    │
│                                                                     │
│  User, UserSession, OAuthToken, OAuthState,                        │
│  OAuthExchangeCode, AllowedUser, AuditLog                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Cross-Cutting Concerns

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Cross-Cutting Services                         │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ SecurityService  │  │ Logging Service  │  │  Config Service  │ │
│  │                  │  │                  │  │                  │ │
│  │ - encrypt()      │  │ - structure logs │  │ - env vars       │ │
│  │ - decrypt()      │  │ - filter secrets │  │ - validation     │ │
│  │ - hash_pwd()     │  │ - JSON output    │  │ - defaults       │ │
│  │ - verify_pwd()   │  │                  │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  Used by all layers                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### OAuth Authentication Flow

```
┌──────┐           ┌──────────┐           ┌─────────┐           ┌─────────┐
│Client│           │Auth      │           │HH API   │           │Database │
│      │           │Service   │           │         │           │         │
└──┬───┘           └────┬─────┘           └────┬────┘           └────┬────┘
   │                    │                      │                     │
   │ 1. GET /auth/login │                      │                     │
   ├───────────────────>│                      │                     │
   │                    │                      │                     │
   │                    │ 2. Generate state    │                     │
   │                    ├──────────────────────┼─────────────────────>
   │                    │    Store state       │                     │
   │                    │                      │                     │
   │ 3. 302 Redirect to HH                     │                     │
   │<───────────────────┤                      │                     │
   │                    │                      │                     │
   │ 4. User authorizes on HH                  │                     │
   ├──────────────────────────────────────────>│                     │
   │                                           │                     │
   │ 5. 302 /callback?code=xxx&state=yyy       │                     │
   │<──────────────────────────────────────────┤                     │
   │                    │                      │                     │
   │ 6. GET /callback   │                      │                     │
   ├───────────────────>│                      │                     │
   │                    │                      │                     │
   │                    │ 7. Validate state    │                     │
   │                    ├──────────────────────┼─────────────────────>
   │                    │                      │                     │
   │                    │ 8. Exchange code for tokens               │
   │                    ├─────────────────────>│                     │
   │                    │<─────────────────────┤                     │
   │                    │  access + refresh    │                     │
   │                    │                      │                     │
   │                    │ 9. Get user info     │                     │
   │                    ├─────────────────────>│                     │
   │                    │<─────────────────────┤                     │
   │                    │   User data          │                     │
   │                    │                      │                     │
   │                    │ 10. Check whitelist  │                     │
   │                    ├──────────────────────┼─────────────────────>
   │                    │<─────────────────────┼─────────────────────┤
   │                    │    Allowed: true     │                     │
   │                    │                      │                     │
   │                    │ 11. Encrypt & save tokens                 │
   │                    ├──────────────────────┼─────────────────────>
   │                    │                      │                     │
   │                    │ 12. Create exchange_code                  │
   │                    ├──────────────────────┼─────────────────────>
   │                    │                      │                     │
   │ 13. HTML with exchange_code               │                     │
   │<───────────────────┤                      │                     │
   │                    │                      │                     │
```

### Token Retrieval Flow

```
┌──────┐           ┌──────────┐           ┌─────────┐
│Client│           │Auth      │           │Database │
│      │           │Service   │           │         │
└──┬───┘           └────┬─────┘           └────┬────┘
   │                    │                      │
   │ 1. POST /auth/exchange                    │
   │    {exchange_code}                        │
   ├───────────────────>│                      │
   │                    │                      │
   │                    │ 2. Validate code     │
   │                    ├─────────────────────>│
   │                    │<─────────────────────┤
   │                    │   User ID            │
   │                    │                      │
   │                    │ 3. Create session    │
   │                    ├─────────────────────>│
   │                    │                      │
   │ 4. Return session_id                      │
   │<───────────────────┤                      │
   │                    │                      │
   │ 5. POST /auth/token                       │
   │    {session_id}                           │
   ├───────────────────>│                      │
   │                    │                      │
   │                    │ 6. Validate session  │
   │                    ├─────────────────────>│
   │                    │<─────────────────────┤
   │                    │   Session valid      │
   │                    │                      │
   │                    │ 7. Get token         │
   │                    ├─────────────────────>│
   │                    │<─────────────────────┤
   │                    │  Encrypted token     │
   │                    │                      │
   │                    │ 8. Decrypt token     │
   │                    │                      │
   │                    │ 9. Check expiration  │
   │                    │  (auto-refresh if needed)
   │                    │                      │
   │ 10. Return access_token                   │
   │<───────────────────┤                      │
   │                    │                      │
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐         ┌──────────────────┐
│  AllowedUser    │         │      User        │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │         │ id (PK)          │
│ hh_user_id      │───────┐ │ hh_user_id (UQ)  │
│ comment         │       │ │ email            │
│ is_active       │       │ │ full_name        │
│ created_at      │       │ │ is_active        │
└─────────────────┘       │ │ created_at       │
                          │ │ updated_at       │
                          │ └────┬─────────────┘
                          │      │
                          │      │ 1:N
                          │      │
                          │      ├─────────────────────────────────┐
                          │      │                                 │
                          │      ▼                                 ▼
        ┌─────────────────┴──────────────┐          ┌─────────────────────┐
        │      UserSession                │          │     OAuthToken      │
        ├────────────────────────────────┤          ├─────────────────────┤
        │ id (PK)                        │          │ id (PK)             │
        │ user_id (FK) ───────────────┐  │          │ user_id (FK) ───┐   │
        │ session_id (UQ)             │  │          │ encrypted_access│   │
        │ created_at                  │  │          │ encrypted_refresh   │
        │ expires_at                  │  │          │ expires_at          │
        │ last_activity               │  │          │ is_revoked          │
        └────────────────────────────┬┘  │          │ created_at          │
                                     │   │          │ updated_at          │
                                     │   │          └─────────────────────┘
                                     │   │
                                     │   │
                                     │   │
                                     │   └─────────────┐
                                     │                 │
                                     ▼                 ▼
                          ┌─────────────────┐  ┌──────────────────┐
                          │   AuditLog      │  │  OAuthState      │
                          ├─────────────────┤  ├──────────────────┤
                          │ id (PK)         │  │ id (PK)          │
                          │ event_type      │  │ state_token (UQ) │
                          │ user_id (FK)    │  │ created_at       │
                          │ event_metadata  │  │ expires_at       │
                          │ created_at      │  │ used_at          │
                          └─────────────────┘  └──────────────────┘

                                     ┌──────────────────────┐
                                     │ OAuthExchangeCode    │
                                     ├──────────────────────┤
                                     │ id (PK)              │
                                     │ exchange_code (UQ)   │
                                     │ user_id (FK)         │
                                     │ created_at           │
                                     │ expires_at           │
                                     │ used_at              │
                                     └──────────────────────┘
```

### Table Descriptions

#### User
Core user information fetched from HeadHunter.
- **Primary Key**: `id`
- **Unique Index**: `hh_user_id`
- **Relationships**: 1:N with UserSession, OAuthToken, AuditLog

#### AllowedUser (Whitelist)
Controls which HH users can authenticate.
- **Primary Key**: `id`
- **Unique Index**: `hh_user_id`
- **Business Rule**: User must exist here with `is_active=true` to authenticate

#### UserSession
Active user sessions with expiration.
- **Primary Key**: `id`
- **Unique Index**: `session_id`
- **Foreign Key**: `user_id` → User
- **TTL**: Configurable (default 720 hours / 30 days)

#### OAuthToken
Encrypted HeadHunter access and refresh tokens.
- **Primary Key**: `id`
- **Foreign Key**: `user_id` → User
- **Encryption**: Fernet symmetric encryption
- **Business Rule**: Only one active token per user (others marked `is_revoked=true`)

#### OAuthState
CSRF protection tokens for OAuth flow.
- **Primary Key**: `id`
- **Unique Index**: `state_token`
- **TTL**: 10 minutes
- **One-time use**: `used_at` marks when consumed

#### OAuthExchangeCode
Temporary codes for client to exchange for session.
- **Primary Key**: `id`
- **Unique Index**: `exchange_code`
- **TTL**: 5 minutes
- **One-time use**: `used_at` marks when exchanged

#### AuditLog
Event logging for security and compliance.
- **Primary Key**: `id`
- **Foreign Key**: `user_id` → User (nullable for system events)
- **Fields**: `event_type`, `event_metadata` (JSONB)
- **Retention**: Recommend archiving after 90 days

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layer 1: Network                            │
│  • HTTPS/TLS 1.2+                                                   │
│  • Rate limiting (100 req/min)                                      │
│  • IP whitelisting (optional)                                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         Layer 2: Application                        │
│  • HTTP Basic Auth (admin endpoints)                                │
│  • Session validation                                               │
│  • CSRF protection (OAuth state)                                    │
│  • Input validation (Pydantic)                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         Layer 3: Data                               │
│  • Token encryption (Fernet AES-128)                                │
│  • Password hashing (bcrypt)                                        │
│  • Whitelist-based access                                           │
│  • Audit logging                                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         Layer 4: Infrastructure                     │
│  • Database encryption at rest                                      │
│  • Secrets management (env vars)                                    │
│  • Non-root container user                                          │
│  • Minimal container image                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Token Encryption Flow

```
┌──────────────┐
│ Plain Token  │
│ (from HH)    │
└──────┬───────┘
       │
       │ Encrypt with Fernet
       │ (AES-128-CBC + HMAC)
       │
       ▼
┌──────────────────┐
│ Encrypted Token  │
│ (binary)         │
└──────┬───────────┘
       │
       │ Base64 encode
       │
       ▼
┌──────────────────┐
│ Stored in DB     │
│ (text)           │
└──────────────────┘

When needed:
┌──────────────────┐
│ Read from DB     │
└──────┬───────────┘
       │
       │ Base64 decode
       │
       ▼
┌──────────────────┐
│ Encrypted Token  │
└──────┬───────────┘
       │
       │ Decrypt with Fernet
       │
       ▼
┌──────────────────┐
│ Plain Token      │
│ (return to user) │
└──────────────────┘
```

### Authentication Mechanisms

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Public Endpoints                               │
│  /health, /metrics, /auth/login, /auth/callback                    │
│  No authentication required                                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      User Endpoints                                 │
│  /auth/exchange, /auth/token, /auth/refresh, /users/me            │
│  Requires: session_id (query param or JSON body)                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Admin Endpoints                                │
│  /admin/*                                                           │
│  Requires: HTTP Basic Auth (username + bcrypt password)            │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Docker Compose Deployment

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                 │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    auth-network (bridge)                      │ │
│  │                                                               │ │
│  │  ┌──────────────────────┐      ┌────────────────────────┐   │ │
│  │  │  auth-service-app    │      │ auth-service-postgres  │   │ │
│  │  ├──────────────────────┤      ├────────────────────────┤   │ │
│  │  │ • Python 3.12        │      │ • PostgreSQL 17        │   │ │
│  │  │ • FastAPI + Uvicorn  │◄────►│ • Port: 5432          │   │ │
│  │  │ • 4 workers          │      │ • Volume: pg_data      │   │ │
│  │  │ • Port: 8000         │      │ • Health check enabled │   │ │
│  │  │ • Health check       │      └────────────────────────┘   │ │
│  │  │ • Non-root user      │                                   │ │
│  │  └──────────────────────┘                                   │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Port Mapping:                                                      │
│  • 8000:8000 → Auth Service                                        │
│  • 5432:5432 → PostgreSQL                                          │
│                                                                     │
│  Volumes:                                                           │
│  • postgres_data → /var/lib/postgresql/data                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Production Deployment with Reverse Proxy

```
                              ┌────────────────┐
                              │   Internet     │
                              └────────┬───────┘
                                       │
                                       │ HTTPS
                                       │
                              ┌────────▼───────┐
                              │  Load Balancer │
                              │  (Nginx/HAProxy)│
                              └────────┬───────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
           ┌────────▼───────┐ ┌───────▼────────┐ ┌──────▼────────┐
           │  Auth Service  │ │  Auth Service  │ │ Auth Service  │
           │   Instance 1   │ │   Instance 2   │ │  Instance N   │
           └────────┬───────┘ └───────┬────────┘ └──────┬────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                              ┌────────▼───────┐
                              │   PostgreSQL   │
                              │   (Primary)    │
                              └────────┬───────┘
                                       │
                              ┌────────▼───────┐
                              │   PostgreSQL   │
                              │   (Replica)    │
                              └────────────────┘
```

### Container Build Process

```
┌─────────────────┐
│  Dockerfile     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Stage 1: Builder                │
│  • Base: python:3.12-slim               │
│  • Install build dependencies           │
│  • Install Python packages              │
│  • Output: /root/.local                 │
└────────┬────────────────────────────────┘
         │
         │ Copy artifacts
         ▼
┌─────────────────────────────────────────┐
│         Stage 2: Runtime                │
│  • Base: python:3.12-slim               │
│  • Copy Python packages from builder    │
│  • Copy application code                │
│  • Create non-root user (appuser)       │
│  • Set CMD: uvicorn                     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Final Image    │
│  Size: ~300 MB  │
└─────────────────┘
```

## Technology Stack

### Backend Framework
- **FastAPI 0.104+**: Modern async web framework
  - Automatic OpenAPI docs
  - Pydantic integration
  - Async/await support
  - Dependency injection

### Database
- **PostgreSQL 17**: Relational database
  - ACID compliance
  - JSONB support (for metadata)
  - Strong consistency
  - Connection pooling

- **SQLAlchemy 2.0**: ORM
  - Async support
  - Type hints (Mapped)
  - Migrations via Alembic
  - Repository pattern

### Security
- **cryptography (Fernet)**: Token encryption
  - AES-128-CBC
  - HMAC authentication
  - Time-based rotation support

- **bcrypt**: Password hashing
  - Work factor: 12
  - Salt generation
  - Timing-safe comparison

### HTTP Client
- **httpx**: Async HTTP client
  - HTTP/2 support
  - Timeout configuration
  - Connection pooling
  - Retry logic

### Logging
- **structlog**: Structured logging
  - JSON output
  - Context binding
  - Sensitive data filtering
  - Processor pipeline

### Server
- **Uvicorn**: ASGI server
  - Worker processes
  - Graceful shutdown
  - HTTP/1.1 and HTTP/2
  - WebSocket support

### Containerization
- **Docker**: Containerization
  - Multi-stage builds
  - Health checks
  - Non-root user

- **Docker Compose**: Orchestration
  - Service dependencies
  - Network isolation
  - Volume management
  - Environment configuration

### Dependencies Summary

```python
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0

# Database
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Security
cryptography==41.0.7
bcrypt==4.1.1

# HTTP Client
httpx==0.25.2

# Validation & Schemas
pydantic==2.5.0
pydantic-settings==2.1.0

# Logging
structlog==23.2.0

# Rate Limiting
slowapi==0.1.9

# Templates
jinja2==3.1.2

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
aiosqlite==0.19.0
```

## Scalability Considerations

### Horizontal Scaling
- Stateless service design
- Session data in database (not in-memory)
- Multiple instances behind load balancer
- Database connection pooling

### Vertical Scaling
- Configurable worker count
- Database connection pool size
- Async I/O for concurrency

### Performance Optimizations
- Database indexes on frequently queried fields
- Connection pooling (DB and HTTP)
- Prepared statements (SQLAlchemy)
- Token encryption caching (future enhancement)

### Monitoring Points
- Request rate and latency
- Database connection pool usage
- Token encryption/decryption time
- HH API response times
- Active session count

## Future Enhancements

### Potential Improvements
1. **Redis for Sessions**: Move sessions to Redis for faster access
2. **Token Caching**: Cache decrypted tokens temporarily (1-5 min)
3. **Rate Limiting per User**: Track by session_id, not just IP
4. **Webhook Support**: Notify client apps of token refresh
5. **Multi-tenancy**: Support multiple HH applications
6. **GraphQL API**: Alternative to REST
7. **gRPC Support**: For service-to-service communication
8. **Metrics Dashboard**: Grafana + Prometheus
9. **Distributed Tracing**: OpenTelemetry integration
10. **Read Replicas**: Database read scaling
