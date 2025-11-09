#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Auth Service API
"""
import httpx
from base64 import b64encode

# Базовый URL
BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def get_auth_header():
    """Создать Basic Auth заголовок"""
    credentials = f"{ADMIN_USER}:{ADMIN_PASS}"
    encoded = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

def test_health():
    """Проверка health endpoint"""
    print("=" * 50)
    print("1. Health Check")
    print("=" * 50)
    response = httpx.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_root():
    """Проверка root endpoint"""
    print("=" * 50)
    print("2. Root Endpoint")
    print("=" * 50)
    response = httpx.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_add_to_whitelist():
    """Добавление пользователя в whitelist"""
    print("=" * 50)
    print("3. Add to Whitelist")
    print("=" * 50)
    data = {
        "hh_user_id": "123456789",
        "description": "Test user from API test"
    }
    response = httpx.post(
        f"{BASE_URL}/admin/whitelist",
        json=data,
        headers=get_auth_header()
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_get_whitelist():
    """Получение списка whitelist"""
    print("=" * 50)
    print("4. Get Whitelist")
    print("=" * 50)
    response = httpx.get(
        f"{BASE_URL}/admin/whitelist",
        params={"active_only": True},
        headers=get_auth_header(),
        auth=(ADMIN_USER, ADMIN_PASS)  # httpx автоматически создаст Basic Auth
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_get_statistics():
    """Получение статистики"""
    print("=" * 50)
    print("5. Get Statistics")
    print("=" * 50)
    response = httpx.get(
        f"{BASE_URL}/admin/statistics",
        headers=get_auth_header(),
        auth=(ADMIN_USER, ADMIN_PASS)
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_auth_login():
    """Тест OAuth login endpoint"""
    print("=" * 50)
    print("6. OAuth Login (должен вернуть redirect)")
    print("=" * 50)
    response = httpx.get(
        f"{BASE_URL}/auth/login",
        follow_redirects=False
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 307:
        print(f"Redirect to: {response.headers.get('location')}\n")
    else:
        print(f"Response: {response.text}\n")

if __name__ == "__main__":
    print("\n🚀 Testing Auth Service v2 API\n")

    try:
        test_health()
        test_root()
        test_add_to_whitelist()
        test_get_whitelist()
        test_get_statistics()
        test_auth_login()

        print("✅ All tests completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
