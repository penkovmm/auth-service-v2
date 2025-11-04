# Deployment Checklist

## Pre-Deployment

### 1. Environment Setup

#### Required Information
- [ ] HeadHunter OAuth credentials
  - [ ] `HH_CLIENT_ID` obtained from HH
  - [ ] `HH_CLIENT_SECRET` obtained from HH
  - [ ] `HH_APP_TOKEN` obtained from HH
  - [ ] `HH_REDIRECT_URI` configured (must match HH app settings)
  - [ ] `HH_USER_AGENT` set with contact email

#### Generate Secrets
- [ ] Encryption key generated
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- [ ] Admin password hash generated
  ```bash
  python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"
  ```
- [ ] Strong PostgreSQL password chosen (min 16 chars)

#### Configuration File
- [ ] Copy `.env.example` to `.env`
  ```bash
  cp .env.example .env
  ```
- [ ] Update all placeholder values in `.env`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure `LOG_LEVEL=INFO` (or WARNING for production)

### 2. Infrastructure

#### Server Requirements
- [ ] Server meets minimum requirements:
  - [ ] 2 CPU cores (4 recommended)
  - [ ] 2 GB RAM (4 GB recommended)
  - [ ] 20 GB disk space (50 GB recommended)
  - [ ] Ubuntu 20.04+ or similar Linux distribution
- [ ] Docker installed (version 20.10+)
  ```bash
  docker --version
  ```
- [ ] Docker Compose installed (version 2.0+)
  ```bash
  docker-compose --version
  ```

#### Network & DNS
- [ ] Domain name configured (e.g., `auth.yourdomain.com`)
- [ ] DNS A record points to server IP
- [ ] SSL/TLS certificate obtained (Let's Encrypt or commercial)
- [ ] Firewall rules configured:
  - [ ] Port 80 (HTTP) open for Let's Encrypt validation
  - [ ] Port 443 (HTTPS) open for API access
  - [ ] Port 22 (SSH) restricted to admin IPs
  - [ ] Port 8000 accessible only from reverse proxy (optional)
  - [ ] Port 5432 blocked from internet

### 3. Code & Database

#### Code Deployment
- [ ] Code repository cloned to server
  ```bash
  git clone <repository_url> /opt/auth-service
  cd /opt/auth-service
  ```
- [ ] Checkout production branch/tag
  ```bash
  git checkout main  # or specific version tag
  ```
- [ ] `.env` file placed in project root
- [ ] File permissions set correctly
  ```bash
  chmod 600 .env
  ```

#### Database
- [ ] PostgreSQL data volume prepared
  ```bash
  docker volume create postgres_data
  ```
- [ ] Database backup strategy planned
- [ ] Backup storage location configured

### 4. Security Hardening

#### Application Security
- [ ] All secrets in `.env` file (never in code)
- [ ] `.env` file excluded from Git (check `.gitignore`)
- [ ] Strong admin password set
- [ ] Encryption key securely stored
- [ ] Session expiration configured appropriately
- [ ] Rate limiting enabled
- [ ] CORS configured (if needed)

#### Server Security
- [ ] Non-root user created for running services
- [ ] SSH key-based authentication enabled
- [ ] SSH password authentication disabled
- [ ] Fail2ban or similar installed
- [ ] Automatic security updates enabled
- [ ] Server timezone set to UTC
  ```bash
  timedatectl set-timezone UTC
  ```

## Deployment

### 1. Build & Start Services

#### Build Docker Images
- [ ] Build application image
  ```bash
  docker-compose build
  ```
- [ ] Verify image built successfully
  ```bash
  docker images | grep auth-service
  ```

#### Start Services
- [ ] Start all services
  ```bash
  docker-compose up -d
  ```
- [ ] Check service status
  ```bash
  docker-compose ps
  ```
- [ ] All services should show "Up" and "healthy"

#### Verify Logs
- [ ] Check auth-service logs
  ```bash
  docker-compose logs -f auth-service
  ```
- [ ] No errors during startup
- [ ] Migrations applied successfully
- [ ] Application started on port 8000

### 2. Database Initialization

#### Verify Database
- [ ] Database created successfully
  ```bash
  docker-compose exec postgres psql -U authuser -d auth_service -c "\dt"
  ```
- [ ] All 7 tables exist:
  - [ ] `users`
  - [ ] `user_sessions`
  - [ ] `oauth_tokens`
  - [ ] `oauth_states`
  - [ ] `oauth_exchange_codes`
  - [ ] `allowed_users`
  - [ ] `audit_log`

#### Seed Data
- [ ] Initial whitelist user exists
  ```bash
  docker-compose exec postgres psql -U authuser -d auth_service \
    -c "SELECT * FROM allowed_users;"
  ```
- [ ] Add additional users to whitelist (if needed)
  ```bash
  curl -X POST http://localhost:8000/admin/users/allow \
    -u admin:password \
    -H "Content-Type: application/json" \
    -d '{"hh_user_id": "12345678", "comment": "Admin user"}'
  ```

### 3. Reverse Proxy Setup (Nginx)

#### Install Nginx
- [ ] Nginx installed
  ```bash
  sudo apt install nginx
  ```

#### SSL Certificate
- [ ] Certbot installed
  ```bash
  sudo apt install certbot python3-certbot-nginx
  ```
- [ ] SSL certificate obtained
  ```bash
  sudo certbot certonly --nginx -d auth.yourdomain.com
  ```

#### Nginx Configuration
- [ ] Nginx config file created
  ```bash
  sudo nano /etc/nginx/sites-available/auth-service
  ```
- [ ] Configuration includes:
  - [ ] SSL/TLS settings
  - [ ] Proxy headers
  - [ ] Security headers
  - [ ] Rate limiting (optional, additional layer)
- [ ] Symlink created
  ```bash
  sudo ln -s /etc/nginx/sites-available/auth-service /etc/nginx/sites-enabled/
  ```
- [ ] Nginx config tested
  ```bash
  sudo nginx -t
  ```
- [ ] Nginx reloaded
  ```bash
  sudo systemctl reload nginx
  ```

### 4. Health Checks

#### Service Health
- [ ] Health endpoint responds
  ```bash
  curl http://localhost:8000/health
  ```
  Expected: `{"status": "healthy", ...}`

- [ ] Health check via domain
  ```bash
  curl https://auth.yourdomain.com/health
  ```

#### Database Connectivity
- [ ] Database accepts connections
  ```bash
  docker-compose exec postgres pg_isready -U authuser
  ```

#### API Endpoints
- [ ] Login endpoint accessible
  ```bash
  curl -I https://auth.yourdomain.com/auth/login
  ```
  Expected: 302 redirect

- [ ] Admin endpoint requires auth
  ```bash
  curl -I https://auth.yourdomain.com/admin/users
  ```
  Expected: 401 without credentials

- [ ] Admin endpoint works with auth
  ```bash
  curl -u admin:password https://auth.yourdomain.com/admin/users
  ```
  Expected: JSON response with users

### 5. Monitoring Setup

#### Prometheus (Optional)
- [ ] Metrics endpoint accessible
  ```bash
  curl https://auth.yourdomain.com/metrics
  ```
- [ ] Prometheus configured to scrape metrics
- [ ] Grafana dashboard created (optional)

#### Health Monitoring
- [ ] Uptime monitor configured (e.g., UptimeRobot, Pingdom)
- [ ] Health check URL: `https://auth.yourdomain.com/health`
- [ ] Alert notifications configured

#### Log Monitoring
- [ ] Log aggregation configured (optional: ELK, Loki)
- [ ] Error alerts configured
- [ ] Log retention policy set

## Post-Deployment

### 1. Functional Testing

#### OAuth Flow
- [ ] Navigate to `https://auth.yourdomain.com/auth/login`
- [ ] Redirected to HeadHunter OAuth page
- [ ] Authorize with whitelisted user
- [ ] Redirected back to callback
- [ ] Exchange code received on success page
- [ ] Exchange code can be exchanged for session
  ```bash
  curl -X POST https://auth.yourdomain.com/auth/exchange \
    -H "Content-Type: application/json" \
    -d '{"exchange_code": "CODE_FROM_PAGE"}'
  ```
- [ ] Session ID received
- [ ] Session ID can retrieve access token
  ```bash
  curl -X POST https://auth.yourdomain.com/auth/token \
    -H "Content-Type: application/json" \
    -d '{"session_id": "SESSION_ID"}'
  ```
- [ ] Access token works with HH API
  ```bash
  curl https://api.hh.ru/me \
    -H "Authorization: Bearer ACCESS_TOKEN"
  ```

#### Admin Functions
- [ ] List users
  ```bash
  curl -u admin:password https://auth.yourdomain.com/admin/users
  ```
- [ ] Add user to whitelist
- [ ] View active sessions
- [ ] Terminate session
- [ ] View audit log

### 2. Security Verification

#### SSL/TLS
- [ ] SSL Labs scan performed: https://www.ssllabs.com/ssltest/
- [ ] Grade A or A+ achieved
- [ ] TLS 1.2+ only
- [ ] Strong ciphers enabled

#### Security Headers
- [ ] Security headers present:
  ```bash
  curl -I https://auth.yourdomain.com
  ```
  - [ ] `Strict-Transport-Security`
  - [ ] `X-Frame-Options`
  - [ ] `X-Content-Type-Options`

#### Access Control
- [ ] Non-whitelisted user cannot authenticate
- [ ] Admin endpoints require authentication
- [ ] Invalid session IDs rejected
- [ ] Expired exchange codes rejected

### 3. Backup & Recovery

#### Initial Backup
- [ ] Create first database backup
  ```bash
  docker-compose exec postgres pg_dump -U authuser auth_service > initial_backup.sql
  ```
- [ ] Store backup securely
- [ ] Test backup restoration
  ```bash
  cat initial_backup.sql | \
    docker-compose exec -T postgres psql -U authuser -d auth_service
  ```

#### Automated Backups
- [ ] Backup script created (see ADMIN_GUIDE.md)
- [ ] Cron job configured for daily backups
  ```bash
  crontab -e
  # Add: 0 2 * * * /path/to/backup_script.sh
  ```
- [ ] Backup retention policy configured (e.g., 30 days)
- [ ] Backup storage monitored for space

### 4. Documentation

#### Operations Runbook
- [ ] Admin credentials documented (secure location)
- [ ] Emergency contacts listed
- [ ] Escalation procedures defined
- [ ] Common issues and solutions documented

#### Architecture Documentation
- [ ] System architecture diagram created
- [ ] Network diagram created
- [ ] Data flow documented
- [ ] Dependencies listed

## Ongoing Maintenance

### Daily
- [ ] Check service health
  ```bash
  curl https://auth.yourdomain.com/health
  ```
- [ ] Review error logs
  ```bash
  docker-compose logs --tail=100 auth-service | grep ERROR
  ```
- [ ] Verify automatic backup completed

### Weekly
- [ ] Review audit logs
  ```bash
  curl -u admin:password https://auth.yourdomain.com/admin/audit-log?limit=100
  ```
- [ ] Check active sessions
  ```bash
  curl -u admin:password https://auth.yourdomain.com/admin/sessions
  ```
- [ ] Monitor disk space
  ```bash
  df -h
  ```
- [ ] Review whitelist users

### Monthly
- [ ] Update system packages
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- [ ] Update Docker images
  ```bash
  docker-compose pull
  docker-compose up -d
  ```
- [ ] Test backup restoration
- [ ] Review and rotate logs
- [ ] Security audit
- [ ] Performance review

### Quarterly
- [ ] Rotate admin password
- [ ] Review encryption key (plan rotation if needed)
- [ ] Update dependencies
- [ ] Disaster recovery drill
- [ ] Review monitoring alerts and thresholds

## Rollback Plan

### Quick Rollback
If deployment fails, rollback immediately:

1. [ ] Stop new containers
   ```bash
   docker-compose down
   ```

2. [ ] Checkout previous version
   ```bash
   git checkout <previous-tag>
   ```

3. [ ] Restore database backup (if schema changed)
   ```bash
   cat backup_pre_deployment.sql | \
     docker-compose exec -T postgres psql -U authuser -d auth_service
   ```

4. [ ] Start services
   ```bash
   docker-compose up -d
   ```

5. [ ] Verify health
   ```bash
   curl https://auth.yourdomain.com/health
   ```

### Root Cause Analysis
- [ ] Document what went wrong
- [ ] Identify root cause
- [ ] Create fix plan
- [ ] Update deployment checklist if needed

## Troubleshooting

### Service Won't Start
- Check logs: `docker-compose logs auth-service`
- Verify `.env` file exists and has correct values
- Check database connectivity
- Verify port 8000 not in use

### Database Issues
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify `DATABASE_URL` in `.env`
- Check disk space
- Verify migrations applied: `docker-compose exec auth-service alembic current`

### OAuth Not Working
- Verify `HH_CLIENT_ID`, `HH_CLIENT_SECRET` in `.env`
- Check `HH_REDIRECT_URI` matches HH app settings
- Ensure user is in whitelist
- Review audit logs for errors

### SSL Certificate Issues
- Check certificate expiry: `sudo certbot certificates`
- Renew if needed: `sudo certbot renew`
- Verify Nginx config: `sudo nginx -t`

## Sign-Off

### Deployment Team
- [ ] Developer approval: _________________ Date: _______
- [ ] DevOps approval: _________________ Date: _______
- [ ] Security review: _________________ Date: _______

### Production Readiness
- [ ] All pre-deployment checks passed
- [ ] All deployment steps completed
- [ ] All post-deployment tests passed
- [ ] Monitoring configured and operational
- [ ] Backups configured and tested
- [ ] Rollback plan documented and tested
- [ ] Team trained on operations procedures

### Go-Live Confirmation
- [ ] Service is live: _________________ Date/Time: _______
- [ ] No critical issues detected
- [ ] Monitoring shows healthy status
- [ ] Users can authenticate successfully

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Version:** _____________
**Notes:** _____________________________________________
