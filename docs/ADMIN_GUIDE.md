# Administrator Guide

## Table of Contents

- [Overview](#overview)
- [Initial Setup](#initial-setup)
- [User Management](#user-management)
- [Session Management](#session-management)
- [Monitoring](#monitoring)
- [Security](#security)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

This guide covers administrative operations for Auth Service v2. All admin endpoints require HTTP Basic Authentication.

### Admin Credentials

Set in `.env` file:
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=bcrypt_hashed_password_here
```

Generate password hash:
```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"
```

### Admin API Base URL

All admin endpoints are under `/admin`:
- Base URL: `http://localhost:8000/admin`
- Authentication: HTTP Basic Auth
- All requests must include `Authorization` header

### Quick Reference

```bash
# All admin commands use Basic Auth
curl -u admin:password http://localhost:8000/admin/users
```

## Initial Setup

### 1. Verify Admin Access

Test admin credentials:
```bash
curl -u admin:your_password http://localhost:8000/admin/users
```

Expected response:
```json
{
  "users": [...],
  "total": 1
}
```

If you get `401 Unauthorized`:
- Check `ADMIN_USERNAME` in `.env`
- Verify `ADMIN_PASSWORD` is correctly hashed
- Restart service after changing credentials

### 2. Review Initial Whitelist

Check seeded users:
```bash
curl -u admin:password http://localhost:8000/admin/users
```

Default setup includes user `174714255`. Add more users as needed.

### 3. Configure Monitoring

Check health endpoint:
```bash
curl http://localhost:8000/health
```

Set up monitoring for:
- `/health` - Service health
- `/metrics` - Prometheus metrics
- Database connection
- Disk space

## User Management

### Adding Users to Whitelist

Only users in the whitelist can authenticate.

#### Add Single User

```bash
curl -X POST http://localhost:8000/admin/users/allow \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "hh_user_id": "12345678",
    "comment": "New team member - John Doe"
  }'
```

Response:
```json
{
  "id": 2,
  "hh_user_id": "12345678",
  "comment": "New team member - John Doe",
  "is_active": true,
  "created_at": "2025-01-10T15:30:00Z"
}
```

#### Add Multiple Users (Script)

```bash
#!/bin/bash
# add_users.sh

ADMIN_USER="admin"
ADMIN_PASS="password"
API_URL="http://localhost:8000"

# Array of users to add
users=(
  "12345678:Developer - Alice"
  "87654321:Developer - Bob"
  "11111111:QA - Charlie"
)

for user in "${users[@]}"; do
  IFS=':' read -r hh_id comment <<< "$user"

  echo "Adding user: $hh_id ($comment)"

  curl -X POST "$API_URL/admin/users/allow" \
    -u "$ADMIN_USER:$ADMIN_PASS" \
    -H "Content-Type: application/json" \
    -d "{
      \"hh_user_id\": \"$hh_id\",
      \"comment\": \"$comment\"
    }" \
    -s | jq .

  echo "---"
done
```

Usage:
```bash
chmod +x add_users.sh
./add_users.sh
```

### Listing Users

#### List All Users

```bash
curl -u admin:password http://localhost:8000/admin/users
```

Response:
```json
{
  "users": [
    {
      "id": 1,
      "hh_user_id": "174714255",
      "comment": "Initial admin",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "hh_user_id": "12345678",
      "comment": "Developer - Alice",
      "is_active": true,
      "created_at": "2025-01-10T15:30:00Z"
    }
  ],
  "total": 2
}
```

#### Filter Active Users Only

```bash
curl -u admin:password "http://localhost:8000/admin/users?active_only=true"
```

#### Export Users to CSV

```bash
#!/bin/bash
# export_users.sh

curl -u admin:password http://localhost:8000/admin/users -s | \
  jq -r '.users[] | [.hh_user_id, .comment, .is_active, .created_at] | @csv' > users.csv
```

### Removing Users

#### Remove Single User

```bash
curl -X DELETE http://localhost:8000/admin/users/12345678 \
  -u admin:password
```

Response:
```json
{
  "message": "User removed from whitelist"
}
```

**Note**: Removing a user:
- Sets `is_active = false` (soft delete)
- User cannot authenticate anymore
- Existing sessions remain active until expiration
- To immediately revoke access, also terminate their sessions

#### Remove User and Sessions

```bash
#!/bin/bash
# revoke_user.sh

HH_USER_ID="12345678"

# Get user's sessions
sessions=$(curl -u admin:password http://localhost:8000/admin/sessions -s | \
  jq -r ".sessions[] | select(.user.hh_user_id == \"$HH_USER_ID\") | .id")

# Terminate all sessions
for session_id in $sessions; do
  echo "Terminating session: $session_id"
  curl -X DELETE "http://localhost:8000/admin/sessions/$session_id" \
    -u admin:password
done

# Remove from whitelist
echo "Removing user from whitelist"
curl -X DELETE "http://localhost:8000/admin/users/$HH_USER_ID" \
  -u admin:password
```

## Session Management

### Viewing Active Sessions

#### List All Sessions

```bash
curl -u admin:password http://localhost:8000/admin/sessions
```

Response:
```json
{
  "sessions": [
    {
      "id": "session_abc123...",
      "user_id": 1,
      "user": {
        "hh_user_id": "174714255",
        "full_name": "Иван Иванов",
        "email": "ivan@example.com"
      },
      "created_at": "2025-01-10T10:00:00Z",
      "expires_at": "2025-02-09T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### Filter Sessions by User

```bash
curl -u admin:password "http://localhost:8000/admin/sessions" -s | \
  jq '.sessions[] | select(.user.hh_user_id == "174714255")'
```

#### Find Sessions Expiring Soon

```bash
#!/bin/bash
# expiring_sessions.sh

# Get sessions expiring in next 24 hours
TOMORROW=$(date -u -d "+1 day" +%Y-%m-%dT%H:%M:%S)

curl -u admin:password http://localhost:8000/admin/sessions -s | \
  jq --arg tomorrow "$TOMORROW" \
    '.sessions[] | select(.expires_at < $tomorrow)'
```

### Terminating Sessions

#### Terminate Single Session

```bash
curl -X DELETE http://localhost:8000/admin/sessions/session_abc123 \
  -u admin:password
```

Response:
```json
{
  "message": "Session terminated"
}
```

**Use cases:**
- Suspicious activity detected
- User reported unauthorized access
- Forcing re-authentication
- User left the organization

#### Terminate All User Sessions

```bash
#!/bin/bash
# terminate_user_sessions.sh

HH_USER_ID="$1"

if [ -z "$HH_USER_ID" ]; then
  echo "Usage: $0 <hh_user_id>"
  exit 1
fi

sessions=$(curl -u admin:password http://localhost:8000/admin/sessions -s | \
  jq -r ".sessions[] | select(.user.hh_user_id == \"$HH_USER_ID\") | .id")

count=0
for session_id in $sessions; do
  echo "Terminating session: $session_id"
  curl -X DELETE "http://localhost:8000/admin/sessions/$session_id" \
    -u admin:password -s
  ((count++))
done

echo "Terminated $count sessions for user $HH_USER_ID"
```

Usage:
```bash
./terminate_user_sessions.sh 12345678
```

#### Terminate All Sessions (Emergency)

```bash
#!/bin/bash
# terminate_all_sessions.sh

echo "WARNING: This will terminate ALL active sessions!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted"
  exit 0
fi

sessions=$(curl -u admin:password http://localhost:8000/admin/sessions -s | \
  jq -r '.sessions[].id')

count=0
for session_id in $sessions; do
  echo "Terminating: $session_id"
  curl -X DELETE "http://localhost:8000/admin/sessions/$session_id" \
    -u admin:password -s
  ((count++))
done

echo "Terminated $count sessions"
```

## Monitoring

### Audit Log

View all authentication events and administrative actions.

#### View Recent Events

```bash
curl -u admin:password "http://localhost:8000/admin/audit-log?limit=20"
```

Response:
```json
{
  "events": [
    {
      "id": 123,
      "event_type": "login",
      "user_id": 1,
      "event_metadata": {
        "ip": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
      },
      "created_at": "2025-01-10T10:00:00Z"
    },
    {
      "id": 124,
      "event_type": "token_refresh",
      "user_id": 1,
      "event_metadata": {},
      "created_at": "2025-01-10T12:00:00Z"
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

#### Event Types

- `login` - User authenticated successfully
- `logout` - User logged out
- `token_refresh` - Access token refreshed
- `user_allowed` - User added to whitelist (admin action)
- `user_removed` - User removed from whitelist (admin action)
- `session_terminated` - Session terminated by admin

#### Filter by Event Type

```bash
curl -u admin:password http://localhost:8000/admin/audit-log -s | \
  jq '.events[] | select(.event_type == "login")'
```

#### Export Audit Log

```bash
#!/bin/bash
# export_audit.sh

LIMIT=1000
OFFSET=0
OUTPUT="audit_$(date +%Y%m%d_%H%M%S).json"

curl -u admin:password \
  "http://localhost:8000/admin/audit-log?limit=$LIMIT&offset=$OFFSET" \
  -s | jq . > "$OUTPUT"

echo "Exported to $OUTPUT"
```

#### Monitor for Failed Logins

```bash
#!/bin/bash
# monitor_failed_logins.sh

while true; do
  failed=$(curl -u admin:password http://localhost:8000/admin/audit-log?limit=100 -s | \
    jq '[.events[] | select(.event_type == "login_failed")] | length')

  echo "$(date): Failed logins in last 100 events: $failed"

  if [ "$failed" -gt 10 ]; then
    echo "ALERT: High number of failed logins!"
    # Send notification (email, Slack, etc.)
  fi

  sleep 300  # Check every 5 minutes
done
```

### Health Monitoring

#### Basic Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-01-10T10:00:00Z"
}
```

#### Database Health

```bash
# Check database connectivity
docker-compose exec postgres pg_isready -U authuser
```

#### Metrics

```bash
curl http://localhost:8000/metrics
```

Prometheus format metrics for:
- Request counts
- Response times
- Error rates
- Active sessions

### Monitoring Scripts

#### Complete Health Check

```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000"

# Check API health
health=$(curl -s "$API_URL/health" | jq -r '.status')
if [ "$health" != "healthy" ]; then
  echo "ERROR: API unhealthy"
  exit 1
fi

# Check database
db_status=$(docker-compose exec -T postgres pg_isready -U authuser | grep "accepting connections")
if [ -z "$db_status" ]; then
  echo "ERROR: Database not responding"
  exit 1
fi

# Check disk space
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 80 ]; then
  echo "WARNING: Disk usage at ${disk_usage}%"
fi

# Check active sessions
sessions=$(curl -s -u admin:password "$API_URL/admin/sessions" | jq '.total')
echo "Active sessions: $sessions"

echo "All checks passed"
```

## Security

### Password Management

#### Change Admin Password

1. Generate new hash:
```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('new_password'))"
```

2. Update `.env`:
```bash
ADMIN_PASSWORD=$2b$12$new_hash_here
```

3. Restart service:
```bash
docker-compose restart auth-service
```

4. Test new password:
```bash
curl -u admin:new_password http://localhost:8000/admin/users
```

### Encryption Key Rotation

**WARNING**: Rotating encryption key requires migrating existing tokens.

#### Step 1: Generate New Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Step 2: Create Migration Script

```python
# migrate_encryption.py
import asyncio
from app.core.config import settings
from app.core.security import SecurityService
from app.db.database import get_engine, async_session_factory
from app.db.repositories.token import TokenRepository
from cryptography.fernet import Fernet

OLD_KEY = "old_encryption_key_here"
NEW_KEY = "new_encryption_key_here"

async def migrate_tokens():
    old_security = SecurityService(encryption_key=OLD_KEY)
    new_security = SecurityService(encryption_key=NEW_KEY)

    async with async_session_factory() as session:
        token_repo = TokenRepository(session)

        # Get all active tokens
        tokens = await token_repo.get_all_active_tokens()

        for token in tokens:
            # Decrypt with old key
            access_token = old_security.decrypt_token(token.encrypted_access_token)
            refresh_token = None
            if token.encrypted_refresh_token:
                refresh_token = old_security.decrypt_token(token.encrypted_refresh_token)

            # Re-encrypt with new key
            token.encrypted_access_token = new_security.encrypt_token(access_token)
            if refresh_token:
                token.encrypted_refresh_token = new_security.encrypt_token(refresh_token)

        await session.commit()
        print(f"Migrated {len(tokens)} tokens")

if __name__ == "__main__":
    asyncio.run(migrate_tokens())
```

#### Step 3: Execute Migration

```bash
# Set new key in .env but don't restart yet
# Run migration
python migrate_encryption.py

# Restart service with new key
docker-compose restart auth-service
```

### SSL/TLS Configuration

For production, always use HTTPS.

#### Using Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/auth-service

upstream auth_backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name auth.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/auth.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auth.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://auth_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Security Auditing

#### Review Recent Admin Actions

```bash
curl -u admin:password http://localhost:8000/admin/audit-log -s | \
  jq '.events[] | select(.event_type == "user_allowed" or .event_type == "user_removed" or .event_type == "session_terminated")'
```

#### Check for Suspicious Activity

```bash
#!/bin/bash
# security_audit.sh

echo "=== Security Audit Report ==="
echo "Generated: $(date)"
echo

# Check for users added recently
echo "Users added in last 24 hours:"
curl -u admin:password http://localhost:8000/admin/users -s | \
  jq ".users[] | select(.created_at > \"$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S)\")"

echo
echo "Failed login attempts:"
curl -u admin:password http://localhost:8000/admin/audit-log?limit=500 -s | \
  jq '[.events[] | select(.event_type == "login_failed")] | length'

echo
echo "Active sessions count:"
curl -u admin:password http://localhost:8000/admin/sessions -s | jq '.total'

echo
echo "Admin actions in last 24 hours:"
curl -u admin:password http://localhost:8000/admin/audit-log?limit=100 -s | \
  jq "[.events[] | select(.created_at > \"$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S)\" and (.event_type == \"user_allowed\" or .event_type == \"user_removed\" or .event_type == \"session_terminated\"))] | length"
```

## Maintenance

### Database Backup

#### Manual Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U authuser auth_service > \
  "backup_$(date +%Y%m%d_%H%M%S).sql"
```

#### Automated Daily Backups

```bash
#!/bin/bash
# backup_cron.sh

BACKUP_DIR="/path/to/backups"
RETENTION_DAYS=30

# Create backup
BACKUP_FILE="$BACKUP_DIR/auth_service_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T postgres pg_dump -U authuser auth_service > "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"

# Delete old backups
find "$BACKUP_DIR" -name "auth_service_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

Add to crontab:
```bash
crontab -e
# Add line:
0 2 * * * /path/to/backup_cron.sh
```

#### Restore from Backup

```bash
# Stop service
docker-compose stop auth-service

# Restore database
gunzip -c backup_20250110_020000.sql.gz | \
  docker-compose exec -T postgres psql -U authuser -d auth_service

# Start service
docker-compose start auth-service
```

### Log Management

#### View Application Logs

```bash
# Real-time logs
docker-compose logs -f auth-service

# Last 100 lines
docker-compose logs --tail=100 auth-service

# Filter by level
docker-compose logs auth-service | grep ERROR
```

#### Export Logs

```bash
docker-compose logs --no-color auth-service > \
  "logs_$(date +%Y%m%d_%H%M%S).log"
```

#### Log Rotation (with logrotate)

```
# /etc/logrotate.d/auth-service

/var/log/auth-service/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose restart auth-service
    endscript
}
```

### Database Cleanup

#### Remove Expired Sessions

```bash
docker-compose exec postgres psql -U authuser -d auth_service <<SQL
DELETE FROM user_sessions WHERE expires_at < NOW();
SQL
```

#### Archive Old Audit Logs

```bash
#!/bin/bash
# archive_audit_logs.sh

# Archive logs older than 90 days
docker-compose exec -T postgres psql -U authuser -d auth_service <<SQL
-- Copy to archive table
CREATE TABLE IF NOT EXISTS audit_log_archive (LIKE audit_log INCLUDING ALL);

INSERT INTO audit_log_archive
SELECT * FROM audit_log
WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete from main table
DELETE FROM audit_log
WHERE created_at < NOW() - INTERVAL '90 days';
SQL

echo "Archived audit logs older than 90 days"
```

#### Vacuum Database

```bash
docker-compose exec postgres psql -U authuser -d auth_service -c "VACUUM ANALYZE;"
```

### Service Updates

#### Update Service

```bash
# 1. Backup database
docker-compose exec postgres pg_dump -U authuser auth_service > backup_pre_update.sql

# 2. Stop service
docker-compose stop auth-service

# 3. Pull new code
git pull origin main

# 4. Rebuild image
docker-compose build auth-service

# 5. Run migrations
docker-compose run --rm auth-service alembic upgrade head

# 6. Start service
docker-compose up -d auth-service

# 7. Check health
curl http://localhost:8000/health

# 8. Check logs
docker-compose logs -f auth-service
```

## Troubleshooting

### Service Won't Start

#### Check Logs

```bash
docker-compose logs auth-service
```

#### Common Issues

**Database connection error**:
```bash
# Check database is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready -U authuser

# Verify DATABASE_URL in .env
```

**Migration errors**:
```bash
# Check migration status
docker-compose exec auth-service alembic current

# Try running migrations manually
docker-compose exec auth-service alembic upgrade head
```

**Port already in use**:
```bash
# Find process using port
sudo lsof -i :8000

# Change port in .env
APP_PORT=8001
```

### Users Can't Authenticate

#### Check User is in Whitelist

```bash
curl -u admin:password http://localhost:8000/admin/users -s | \
  jq '.users[] | select(.hh_user_id == "12345678")'
```

If not found, add user:
```bash
curl -X POST http://localhost:8000/admin/users/allow \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"hh_user_id": "12345678", "comment": "Added during troubleshooting"}'
```

#### Check HH OAuth Credentials

```bash
# Verify in .env
grep HH_CLIENT .env

# Test HH API connectivity
curl "https://api.hh.ru/me" -H "Authorization: Bearer test_token"
```

### Tokens Not Refreshing

#### Check Refresh Token Validity

```bash
docker-compose exec postgres psql -U authuser -d auth_service <<SQL
SELECT user_id, expires_at, is_revoked, created_at
FROM oauth_tokens
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 1;
SQL
```

#### Force Re-authentication

```bash
# Terminate all user sessions
./terminate_user_sessions.sh 12345678

# User must re-authenticate
```

### High CPU/Memory Usage

#### Check Resource Usage

```bash
docker stats auth-service-app
```

#### Check Active Connections

```bash
docker-compose exec postgres psql -U authuser -d auth_service -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = 'auth_service';"
```

#### Restart Service

```bash
docker-compose restart auth-service
```

## Best Practices

### DO

✅ Regularly backup database (daily minimum)
✅ Monitor audit logs for suspicious activity
✅ Review and clean up old sessions periodically
✅ Use strong admin password and rotate it quarterly
✅ Enable HTTPS in production
✅ Set up automated health checks
✅ Keep service and dependencies updated
✅ Document all manual interventions
✅ Test backup restoration periodically

### DON'T

❌ Share admin credentials
❌ Disable audit logging
❌ Store admin password in plain text
❌ Skip database backups
❌ Ignore health check failures
❌ Add users to whitelist without approval
❌ Run without HTTPS in production
❌ Leave old sessions accumulating
❌ Expose admin endpoints publicly

### Recommended Schedule

**Daily**:
- Check health status
- Review failed login attempts
- Database backup

**Weekly**:
- Review audit logs
- Check disk space
- Clean up expired sessions

**Monthly**:
- Review whitelist
- Update dependencies
- Test backup restoration
- Security audit

**Quarterly**:
- Rotate admin password
- Review and update access controls
- Performance review
- Disaster recovery drill
