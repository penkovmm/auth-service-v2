# API Usage Examples

## Table of Contents

- [Authentication Flow](#authentication-flow)
- [User Management](#user-management)
- [Admin Operations](#admin-operations)
- [Health Monitoring](#health-monitoring)
- [Error Handling](#error-handling)
- [Integration Examples](#integration-examples)

## Authentication Flow

### Complete Authentication Example

#### 1. Browser-based Flow (Recommended)

```javascript
// Frontend JavaScript example
async function authenticateUser() {
    // Redirect user to login
    window.location.href = 'http://localhost:8000/auth/login';
}

// After redirect back, extract exchange code from page
async function completeAuth() {
    // User copies exchange_code from HTML page
    const exchangeCode = document.getElementById('exchange-code').value;

    try {
        // Exchange for session
        const sessionResponse = await fetch('http://localhost:8000/auth/exchange', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exchange_code: exchangeCode })
        });

        if (!sessionResponse.ok) {
            throw new Error('Exchange failed');
        }

        const { session_id, expires_at } = await sessionResponse.json();

        // Store session_id securely (e.g., httpOnly cookie)
        document.cookie = `session_id=${session_id}; Secure; HttpOnly; SameSite=Strict`;

        console.log('Authenticated! Session expires:', expires_at);

        // Get HH access token
        const tokenResponse = await fetch('http://localhost:8000/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id })
        });

        const { access_token } = await tokenResponse.json();

        // Now use access_token to call HH API
        return access_token;

    } catch (error) {
        console.error('Authentication error:', error);
        throw error;
    }
}
```

#### 2. Backend Service Integration (Python)

```python
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class HHAuthClient:
    """Client for HH Auth Service v2"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.access_token: Optional[str] = None

    def get_login_url(self) -> str:
        """Get URL for user to initiate OAuth flow"""
        return f"{self.base_url}/auth/login"

    def exchange_code(self, exchange_code: str) -> dict:
        """Exchange code for session ID"""
        response = requests.post(
            f"{self.base_url}/auth/exchange",
            json={"exchange_code": exchange_code}
        )
        response.raise_for_status()

        data = response.json()
        self.session_id = data["session_id"]
        logger.info(f"Session acquired, expires at {data['expires_at']}")
        return data

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get HH access token (auto-refreshes if expired)"""
        if not self.session_id:
            raise ValueError("No session ID. Call exchange_code first.")

        endpoint = "/auth/refresh" if force_refresh else "/auth/token"

        response = requests.post(
            f"{self.base_url}{endpoint}",
            json={"session_id": self.session_id}
        )
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access_token"]
        return self.access_token

    def logout(self) -> None:
        """Logout and invalidate session"""
        if not self.session_id:
            return

        response = requests.post(
            f"{self.base_url}/auth/logout",
            json={"session_id": self.session_id}
        )
        response.raise_for_status()

        self.session_id = None
        self.access_token = None
        logger.info("Logged out successfully")

    def get_current_user(self) -> dict:
        """Get current user info from auth service"""
        if not self.session_id:
            raise ValueError("No session ID")

        response = requests.get(
            f"{self.base_url}/users/me",
            params={"session_id": self.session_id}
        )
        response.raise_for_status()
        return response.json()

    def call_hh_api(self, endpoint: str, method: str = "GET", **kwargs) -> dict:
        """Make authenticated request to HH API"""
        if not self.access_token:
            self.get_access_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        response = requests.request(
            method=method,
            url=f"https://api.hh.ru{endpoint}",
            headers=headers,
            **kwargs
        )

        # Auto-refresh token on 401
        if response.status_code == 401:
            logger.info("Token expired, refreshing...")
            self.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.request(
                method=method,
                url=f"https://api.hh.ru{endpoint}",
                headers=headers,
                **kwargs
            )

        response.raise_for_status()
        return response.json()


# Usage example
def main():
    client = HHAuthClient()

    # Step 1: Direct user to login
    print(f"Please visit: {client.get_login_url()}")

    # Step 2: User authorizes and gets exchange code
    exchange_code = input("Enter exchange code: ")
    client.exchange_code(exchange_code)

    # Step 3: Get user info
    user = client.get_current_user()
    print(f"Authenticated as: {user['full_name']}")

    # Step 4: Call HH API
    me = client.call_hh_api("/me")
    print(f"HH User: {me['first_name']} {me['last_name']}")

    # Step 5: Logout
    client.logout()


if __name__ == "__main__":
    main()
```

### Token Management

#### Get Token with Auto-Refresh

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your_session_id_here"
  }'
```

Response:
```json
{
  "access_token": "hh_access_token_here",
  "token_type": "Bearer",
  "expires_at": "2025-01-15T12:00:00Z"
}
```

#### Force Token Refresh

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your_session_id_here"
  }'
```

## User Management

### Get Current User Info

```bash
curl -X GET "http://localhost:8000/users/me?session_id=your_session_id"
```

Response:
```json
{
  "id": 1,
  "hh_user_id": "174714255",
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "is_active": true,
  "created_at": "2025-01-10T10:00:00Z",
  "updated_at": "2025-01-10T10:00:00Z"
}
```

### Python Example with Error Handling

```python
import requests
from typing import Optional

def get_user_info(session_id: str, base_url: str = "http://localhost:8000") -> Optional[dict]:
    """Get user info with proper error handling"""
    try:
        response = requests.get(
            f"{base_url}/users/me",
            params={"session_id": session_id},
            timeout=10
        )

        if response.status_code == 401:
            print("Session expired. Please re-authenticate.")
            return None

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info: {e}")
        return None


# Usage
user = get_user_info("your_session_id")
if user:
    print(f"Welcome, {user['full_name']}!")
```

## Admin Operations

All admin endpoints require HTTP Basic Authentication.

### Add User to Whitelist

```bash
curl -X POST http://localhost:8000/admin/users/allow \
  -u admin:your_password \
  -H "Content-Type: application/json" \
  -d '{
    "hh_user_id": "12345678",
    "comment": "New team member"
  }'
```

Response:
```json
{
  "id": 2,
  "hh_user_id": "12345678",
  "comment": "New team member",
  "is_active": true,
  "created_at": "2025-01-10T15:30:00Z"
}
```

### List All Allowed Users

```bash
curl -X GET http://localhost:8000/admin/users \
  -u admin:your_password
```

Response:
```json
{
  "users": [
    {
      "id": 1,
      "hh_user_id": "174714255",
      "comment": "Initial admin user",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "hh_user_id": "12345678",
      "comment": "New team member",
      "is_active": true,
      "created_at": "2025-01-10T15:30:00Z"
    }
  ],
  "total": 2
}
```

### Remove User from Whitelist

```bash
curl -X DELETE http://localhost:8000/admin/users/12345678 \
  -u admin:your_password
```

Response:
```json
{
  "message": "User removed from whitelist"
}
```

### View Active Sessions

```bash
curl -X GET http://localhost:8000/admin/sessions \
  -u admin:your_password
```

Response:
```json
{
  "sessions": [
    {
      "id": "session_id_here",
      "user_id": 1,
      "user": {
        "hh_user_id": "174714255",
        "full_name": "Иван Иванов"
      },
      "created_at": "2025-01-10T10:00:00Z",
      "expires_at": "2025-02-09T10:00:00Z"
    }
  ],
  "total": 1
}
```

### Terminate Session

```bash
curl -X DELETE http://localhost:8000/admin/sessions/session_id_here \
  -u admin:your_password
```

Response:
```json
{
  "message": "Session terminated"
}
```

### View Audit Log

```bash
curl -X GET "http://localhost:8000/admin/audit-log?limit=10&offset=0" \
  -u admin:your_password
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
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### Python Admin Client Example

```python
import requests
from typing import List, Dict, Optional

class AuthServiceAdmin:
    """Admin client for Auth Service v2"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.auth = (username, password)

    def add_user(self, hh_user_id: str, comment: str = "") -> dict:
        """Add user to whitelist"""
        response = requests.post(
            f"{self.base_url}/admin/users/allow",
            auth=self.auth,
            json={"hh_user_id": hh_user_id, "comment": comment}
        )
        response.raise_for_status()
        return response.json()

    def list_users(self) -> List[dict]:
        """List all allowed users"""
        response = requests.get(
            f"{self.base_url}/admin/users",
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()["users"]

    def remove_user(self, hh_user_id: str) -> None:
        """Remove user from whitelist"""
        response = requests.delete(
            f"{self.base_url}/admin/users/{hh_user_id}",
            auth=self.auth
        )
        response.raise_for_status()

    def list_sessions(self) -> List[dict]:
        """List all active sessions"""
        response = requests.get(
            f"{self.base_url}/admin/sessions",
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()["sessions"]

    def terminate_session(self, session_id: str) -> None:
        """Terminate a session"""
        response = requests.delete(
            f"{self.base_url}/admin/sessions/{session_id}",
            auth=self.auth
        )
        response.raise_for_status()

    def get_audit_log(self, limit: int = 100, offset: int = 0) -> dict:
        """Get audit log"""
        response = requests.get(
            f"{self.base_url}/admin/audit-log",
            auth=self.auth,
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()


# Usage example
admin = AuthServiceAdmin(
    base_url="http://localhost:8000",
    username="admin",
    password="your_password"
)

# Add new user
admin.add_user("12345678", "New developer")

# List all users
users = admin.list_users()
print(f"Total users: {len(users)}")

# View sessions
sessions = admin.list_sessions()
for session in sessions:
    print(f"User: {session['user']['full_name']}, Expires: {session['expires_at']}")

# Get recent events
audit = admin.get_audit_log(limit=10)
print(f"Recent events: {audit['total']}")
```

## Health Monitoring

### Health Check

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

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

Response (Prometheus format):
```
# HELP requests_total Total number of requests
# TYPE requests_total counter
requests_total{method="GET",endpoint="/health"} 42

# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{method="POST",endpoint="/auth/token",le="0.1"} 35
```

### Health Check with Monitoring

```python
import requests
import time
from datetime import datetime

def monitor_health(url: str = "http://localhost:8000", interval: int = 60):
    """Monitor service health"""
    while True:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            data = response.json()

            if response.status_code == 200 and data["status"] == "healthy":
                print(f"[{datetime.now()}] ✓ Service healthy")
            else:
                print(f"[{datetime.now()}] ✗ Service unhealthy: {data}")

        except Exception as e:
            print(f"[{datetime.now()}] ✗ Health check failed: {e}")

        time.sleep(interval)


# Usage
monitor_health()
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid or expired exchange code"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Invalid session"
}
```

#### 403 Forbidden
```json
{
  "detail": "User 12345678 is not allowed to access this service"
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "An internal error occurred. Please try again later."
}
```

### Error Handling Best Practices

```python
import requests
from typing import Optional

def safe_api_call(url: str, method: str = "GET", **kwargs) -> Optional[dict]:
    """Make API call with comprehensive error handling"""
    try:
        response = requests.request(method, url, **kwargs)

        # Handle specific status codes
        if response.status_code == 400:
            print(f"Bad request: {response.json().get('detail')}")
            return None

        elif response.status_code == 401:
            print("Unauthorized. Session may have expired.")
            return None

        elif response.status_code == 403:
            print("Forbidden. User not in whitelist.")
            return None

        elif response.status_code == 404:
            print("Resource not found")
            return None

        elif response.status_code >= 500:
            print(f"Server error: {response.status_code}")
            return None

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        print("Request timed out")
        return None

    except requests.exceptions.ConnectionError:
        print("Connection error. Is the service running?")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Usage
result = safe_api_call(
    "http://localhost:8000/users/me",
    params={"session_id": "your_session_id"}
)

if result:
    print(f"User: {result['full_name']}")
```

## Integration Examples

### Django Integration

```python
# settings.py
AUTH_SERVICE_URL = "http://localhost:8000"

# middleware.py
from django.conf import settings
import requests

class HHAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_id = request.COOKIES.get('hh_session_id')

        if session_id:
            try:
                response = requests.get(
                    f"{settings.AUTH_SERVICE_URL}/users/me",
                    params={"session_id": session_id},
                    timeout=5
                )

                if response.status_code == 200:
                    request.hh_user = response.json()
                else:
                    request.hh_user = None

            except:
                request.hh_user = None
        else:
            request.hh_user = None

        return self.get_response(request)

# views.py
from django.shortcuts import redirect
from django.http import JsonResponse

def hh_login(request):
    return redirect(f"{settings.AUTH_SERVICE_URL}/auth/login")

def hh_callback(request):
    # User gets exchange_code from auth service page
    # Store in session and redirect to exchange
    exchange_code = request.GET.get('exchange_code')
    if exchange_code:
        request.session['exchange_code'] = exchange_code
        return redirect('hh_exchange')
    return JsonResponse({"error": "No exchange code"}, status=400)

def hh_exchange(request):
    exchange_code = request.session.pop('exchange_code', None)
    if not exchange_code:
        return JsonResponse({"error": "No exchange code in session"}, status=400)

    response = requests.post(
        f"{settings.AUTH_SERVICE_URL}/auth/exchange",
        json={"exchange_code": exchange_code}
    )

    if response.status_code == 200:
        data = response.json()
        response = redirect('home')
        response.set_cookie('hh_session_id', data['session_id'],
                          httponly=True, secure=True)
        return response

    return JsonResponse({"error": "Exchange failed"}, status=400)
```

### Flask Integration

```python
from flask import Flask, request, redirect, session, jsonify
import requests

app = Flask(__name__)
app.secret_key = 'your-secret-key'

AUTH_SERVICE_URL = "http://localhost:8000"

@app.route('/login')
def login():
    return redirect(f"{AUTH_SERVICE_URL}/auth/login")

@app.route('/exchange')
def exchange():
    exchange_code = request.args.get('exchange_code')
    if not exchange_code:
        return jsonify({"error": "No exchange code"}), 400

    response = requests.post(
        f"{AUTH_SERVICE_URL}/auth/exchange",
        json={"exchange_code": exchange_code}
    )

    if response.status_code == 200:
        data = response.json()
        session['session_id'] = data['session_id']
        return redirect('/')

    return jsonify({"error": "Exchange failed"}), 400

@app.route('/me')
def me():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"error": "Not authenticated"}), 401

    response = requests.get(
        f"{AUTH_SERVICE_URL}/users/me",
        params={"session_id": session_id}
    )

    if response.status_code == 200:
        return jsonify(response.json())

    return jsonify({"error": "Failed to get user"}), response.status_code

@app.route('/logout')
def logout():
    session_id = session.pop('session_id', None)
    if session_id:
        requests.post(
            f"{AUTH_SERVICE_URL}/auth/logout",
            json={"session_id": session_id}
        )
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException, Cookie
from typing import Optional
import httpx

app = FastAPI()

AUTH_SERVICE_URL = "http://localhost:8000"

async def get_current_user(session_id: Optional[str] = Cookie(None)) -> dict:
    """Dependency to get current authenticated user"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/users/me",
            params={"session_id": session_id}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")

    return response.json()

@app.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {"message": f"Hello, {user['full_name']}!"}

@app.get("/hh-resumes")
async def get_resumes(
    user: dict = Depends(get_current_user),
    session_id: str = Cookie(...)
):
    """Example: Fetch resumes from HH API"""
    # Get HH access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/token",
            json={"session_id": session_id}
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to get token")

    access_token = token_response.json()["access_token"]

    # Call HH API
    async with httpx.AsyncClient() as client:
        hh_response = await client.get(
            "https://api.hh.ru/resumes/mine",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    if hh_response.status_code != 200:
        raise HTTPException(status_code=502, detail="HH API error")

    return hh_response.json()
```

## Rate Limiting

The service has built-in rate limiting. Default limits:
- 100 requests per minute per IP
- 1000 requests per hour per IP

When rate limited, you'll receive:
```json
{
  "detail": "Rate limit exceeded"
}
```

HTTP Status: `429 Too Many Requests`

Headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1641819600
```

Handle rate limits in your client:
```python
import time

def api_call_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```
