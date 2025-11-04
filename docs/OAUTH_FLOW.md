# OAuth 2.0 Flow Documentation

## Overview

Auth Service v2 implements OAuth 2.0 Authorization Code flow with HeadHunter API. The service manages the complete authentication lifecycle, token storage, and automatic token refresh.

## Flow Diagram

```
┌─────────┐                                                           ┌──────────────┐
│ Client  │                                                           │ Auth Service │
│  App    │                                                           │     v2       │
└────┬────┘                                                           └──────┬───────┘
     │                                                                       │
     │ 1. Initiate Login                                                    │
     │ GET /auth/login                                                      │
     ├─────────────────────────────────────────────────────────────────────>│
     │                                                                       │
     │ 2. Redirect to HH with state parameter                               │
     │<─────────────────────────────────────────────────────────────────────┤
     │                                                                       │
     │                     ┌──────────────┐                                 │
     │ 3. User authorizes  │ HeadHunter   │                                 │
     ├────────────────────>│   OAuth      │                                 │
     │                     └──────┬───────┘                                 │
     │                            │                                         │
     │ 4. Redirect back with code │                                         │
     │ GET /auth/callback?code=xxx&state=yyy                                │
     │<───────────────────────────┴─────────────────────────────────────────┤
     │                                                                       │
     │ 5. Exchange code for access token (internal)                         │
     │                                                   ┌──────────────┐   │
     │                                                   │ HeadHunter   │   │
     │                                                   │     API      │   │
     │                                                   └──────┬───────┘   │
     │                                                          │           │
     │ 6. Return exchange_code to client                        │           │
     │<─────────────────────────────────────────────────────────┼───────────┤
     │                                                          │           │
     │ 7. Exchange code for session_id                          │           │
     │ POST /auth/exchange {exchange_code}                      │           │
     ├──────────────────────────────────────────────────────────┼──────────>│
     │                                                          │           │
     │ 8. Return session_id                                     │           │
     │<─────────────────────────────────────────────────────────┼───────────┤
     │                                                          │           │
     │ 9. Use session_id to get HH access token                 │           │
     │ POST /auth/token {session_id}                            │           │
     ├──────────────────────────────────────────────────────────┼──────────>│
     │                                                          │           │
     │ 10. Return HH access token (decrypted)                   │           │
     │<─────────────────────────────────────────────────────────┼───────────┤
     │                                                          │           │
     │ 11. Make requests to HH API with token                   │           │
     ├──────────────────────────────────────────────────────────┼──────────>│
     │                                                          │           │
```

## Step-by-Step Process

### Step 1: Initiate Login

Client redirects user to auth service:

```bash
curl -L "http://localhost:8000/auth/login"
```

**Response**: 302 redirect to HeadHunter OAuth page

**What happens:**
1. Service generates a random `state` parameter (CSRF protection)
2. Stores state in database with 10-minute expiration
3. Redirects to `https://hh.ru/oauth/authorize` with:
   - `client_id`: Your HH application ID
   - `response_type=code`
   - `redirect_uri`: Your callback URL
   - `state`: Random token for CSRF protection

### Step 2: User Authorizes on HeadHunter

User logs in to HeadHunter and grants permission to your application. This happens on HH's website, not in your service.

### Step 3: Callback with Authorization Code

HeadHunter redirects back to your service:

```
GET /auth/callback?code=AUTHORIZATION_CODE&state=CSRF_TOKEN
```

**What happens:**
1. Service validates the `state` parameter (CSRF check)
2. Exchanges authorization code for access/refresh tokens with HH API
3. Fetches user info from HH API (`GET /me`)
4. Checks if user is in whitelist
5. Stores encrypted tokens in database
6. Creates a temporary `exchange_code` (5-minute TTL)
7. Renders HTML page with the exchange code

**HTML Response:**
```html
<!DOCTYPE html>
<html>
<head><title>Авторизация успешна</title></head>
<body>
    <h1>Авторизация успешна!</h1>
    <p>Ваш код для обмена на сессию:</p>
    <code>EXCHANGE_CODE_HERE</code>
    <p>Используйте этот код в течение 5 минут для получения session_id</p>
</body>
</html>
```

### Step 4: Exchange Code for Session

Client exchanges the temporary code for a session ID:

```bash
curl -X POST http://localhost:8000/auth/exchange \
  -H "Content-Type: application/json" \
  -d '{"exchange_code": "EXCHANGE_CODE_HERE"}'
```

**Response:**
```json
{
  "session_id": "long_random_session_id_here",
  "expires_at": "2025-01-31T12:00:00Z"
}
```

**What happens:**
1. Service validates the exchange code
2. Creates a user session (720 hours / 30 days default TTL)
3. Returns session ID to client
4. Deletes the exchange code (one-time use)

### Step 5: Get HH Access Token

Client requests the actual HH access token using session ID:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your_session_id_here"}'
```

**Response:**
```json
{
  "access_token": "actual_hh_access_token",
  "token_type": "Bearer",
  "expires_at": "2025-01-15T12:00:00Z"
}
```

**What happens:**
1. Service validates session (exists, not expired)
2. Retrieves encrypted tokens from database
3. Decrypts access token
4. If token expired, automatically refreshes it with HH API
5. Returns decrypted access token to client

### Step 6: Refresh Token (Automatic)

Token refresh happens automatically when you call `/auth/token` with an expired token. You can also force refresh:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your_session_id_here"}'
```

**Response:**
```json
{
  "access_token": "new_hh_access_token",
  "token_type": "Bearer",
  "expires_at": "2025-01-15T12:00:00Z"
}
```

### Step 7: Logout

Terminate session and revoke tokens:

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your_session_id_here"}'
```

**Response:**
```json
{
  "message": "Logout successful"
}
```

**What happens:**
1. Deletes user session
2. Marks all user tokens as revoked in database
3. Tokens are kept in DB for audit purposes but cannot be used

## Security Features

### CSRF Protection

The `state` parameter prevents CSRF attacks:
- Random 32-byte token generated for each login attempt
- Stored in database with 10-minute expiration
- Validated on callback
- Deleted after use (one-time)

### Token Encryption

All tokens are encrypted at rest:
- Uses Fernet (AES-128 CBC with HMAC authentication)
- Encryption key stored in environment variable
- Tokens never logged or exposed in error messages

### Whitelist

Only pre-approved users can authenticate:
- HH user IDs stored in `allowed_users` table
- Checked after user info is fetched from HH
- Returns 403 Forbidden if user not in whitelist

### Session Expiration

Sessions automatically expire:
- Default: 720 hours (30 days)
- Configurable via `SESSION_EXPIRE_HOURS`
- Expired sessions cannot be used
- Background cleanup job recommended

## Error Handling

### Common Errors

**403 Forbidden: User not in whitelist**
```json
{
  "detail": "User 12345678 is not allowed to access this service"
}
```

**Solution**: Admin must add user to whitelist via `/admin/users/allow`

**400 Bad Request: Invalid or expired exchange code**
```json
{
  "detail": "Invalid or expired exchange code"
}
```

**Solution**: Code expires after 5 minutes. User must re-authenticate.

**401 Unauthorized: Invalid session**
```json
{
  "detail": "Invalid session"
}
```

**Solution**: Session expired or doesn't exist. User must re-authenticate.

**400 Bad Request: OAuth state validation failed**
```json
{
  "detail": "Invalid or expired state parameter"
}
```

**Solution**: CSRF token expired (10 min). User must restart login flow.

## Example: Complete Flow in Python

```python
import requests
from urllib.parse import urlparse, parse_qs

# Step 1: Initiate login (user clicks this in browser)
login_url = "http://localhost:8000/auth/login"
print(f"User should visit: {login_url}")

# Step 2-3: User authorizes on HH website (happens in browser)
# HeadHunter redirects to: /auth/callback?code=xxx&state=yyy

# User gets exchange_code from HTML page
exchange_code = input("Enter exchange_code from page: ")

# Step 4: Exchange code for session
response = requests.post(
    "http://localhost:8000/auth/exchange",
    json={"exchange_code": exchange_code}
)
session_data = response.json()
session_id = session_data["session_id"]
print(f"Session ID: {session_id}")

# Step 5: Get HH access token
response = requests.post(
    "http://localhost:8000/auth/token",
    json={"session_id": session_id}
)
token_data = response.json()
access_token = token_data["access_token"]
print(f"Access Token: {access_token}")

# Step 6: Use token to call HH API
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("https://api.hh.ru/me", headers=headers)
user_info = response.json()
print(f"User: {user_info['last_name']} {user_info['first_name']}")

# Step 7: Logout when done
requests.post(
    "http://localhost:8000/auth/logout",
    json={"session_id": session_id}
)
print("Logged out")
```

## Example: JavaScript/Node.js

```javascript
const axios = require('axios');

async function authFlow() {
    // Step 1: User visits login URL in browser
    console.log('User should visit: http://localhost:8000/auth/login');

    // Step 2-3: User completes OAuth on HH
    // Get exchange_code from HTML page
    const exchangeCode = 'EXCHANGE_CODE_FROM_PAGE';

    // Step 4: Exchange for session
    const sessionResponse = await axios.post(
        'http://localhost:8000/auth/exchange',
        { exchange_code: exchangeCode }
    );
    const sessionId = sessionResponse.data.session_id;
    console.log('Session ID:', sessionId);

    // Step 5: Get access token
    const tokenResponse = await axios.post(
        'http://localhost:8000/auth/token',
        { session_id: sessionId }
    );
    const accessToken = tokenResponse.data.access_token;
    console.log('Access Token:', accessToken);

    // Step 6: Use token
    const userResponse = await axios.get('https://api.hh.ru/me', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    console.log('User:', userResponse.data);

    // Step 7: Logout
    await axios.post('http://localhost:8000/auth/logout', {
        session_id: sessionId
    });
    console.log('Logged out');
}

authFlow().catch(console.error);
```

## Best Practices

### For Client Applications

1. **Store session_id securely**
   - Use httpOnly cookies or secure storage
   - Never expose in URLs or client-side JavaScript

2. **Handle token expiration**
   - The service auto-refreshes tokens
   - Always check response status codes
   - Re-authenticate on 401 errors

3. **Implement logout**
   - Call `/auth/logout` when user logs out
   - Clear stored session_id

4. **Error handling**
   - Display user-friendly messages
   - Log errors for debugging
   - Implement retry logic for network errors

### For Service Administrators

1. **Manage whitelist carefully**
   - Only add trusted users
   - Review audit logs regularly
   - Remove users when access should be revoked

2. **Monitor sessions**
   - Check active sessions via `/admin/sessions`
   - Terminate suspicious sessions
   - Implement session limits per user if needed

3. **Rotate encryption keys**
   - Plan key rotation schedule
   - Migrate existing tokens when rotating
   - Keep backups of old keys temporarily

4. **Database maintenance**
   - Archive old audit logs periodically
   - Clean up expired sessions and tokens
   - Monitor database size

## Troubleshooting

### User stuck in OAuth loop

**Symptom**: User keeps getting redirected to HH after login

**Possible causes:**
- User not in whitelist (check logs)
- State parameter expiring too quickly
- Clock skew between services

**Solution:**
```bash
# Check if user is in whitelist
curl -u admin:password http://localhost:8000/admin/users

# Add user if missing
curl -u admin:password -X POST http://localhost:8000/admin/users/allow \
  -H "Content-Type: application/json" \
  -d '{"hh_user_id": "12345678", "comment": "Added for testing"}'
```

### Tokens not refreshing

**Symptom**: Getting 401 errors even after token should refresh

**Possible causes:**
- Refresh token expired or invalid
- HH API issues
- Network connectivity

**Solution:**
```bash
# Check token status in database
docker-compose exec postgres psql -U authuser -d auth_service \
  -c "SELECT user_id, expires_at, is_revoked FROM oauth_tokens WHERE user_id = 1;"

# Force user to re-authenticate
curl -u admin:password -X DELETE http://localhost:8000/admin/sessions/SESSION_ID
```

### Exchange code expired

**Symptom**: "Invalid or expired exchange code" error

**Cause**: 5-minute window between callback and exchange expired

**Solution**: User must restart authentication flow from `/auth/login`

## Configuration

### Environment Variables

Key OAuth-related settings:

```bash
# HeadHunter OAuth credentials
HH_CLIENT_ID=your_client_id
HH_CLIENT_SECRET=your_secret
HH_REDIRECT_URI=http://localhost:8000/auth/callback

# Session settings
SESSION_EXPIRE_HOURS=720          # 30 days
EXCHANGE_CODE_EXPIRE_MINUTES=5    # Exchange code TTL
OAUTH_STATE_EXPIRE_MINUTES=10     # CSRF token TTL

# Security
ENCRYPTION_KEY=your_fernet_key    # For token encryption
```

### Customization

To change OAuth scopes (currently not used, but available):

Edit `app/services/hh_oauth_service.py`:
```python
params = {
    "client_id": self.settings.hh_client_id,
    "response_type": "code",
    "redirect_uri": self.settings.hh_redirect_uri,
    "state": state_token,
    "scope": "read_resumes write_resumes"  # Add scopes here
}
```

Available HH scopes: https://github.com/hhru/api/blob/master/docs/authorization.md
