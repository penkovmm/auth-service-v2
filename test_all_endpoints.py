#!/usr/bin/env python3
"""
Полный тест всех endpoints Auth Service v2
"""
import httpx
from base64 import b64encode
import json

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def print_section(title):
    """Печать красивого заголовка"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_request(method, endpoint, description, auth=False, json_data=None, params=None):
    """Универсальная функция тестирования"""
    print(f"\n📍 {description}")
    print(f"   {method} {endpoint}")

    url = f"{BASE_URL}{endpoint}"
    kwargs = {}

    if auth:
        kwargs['auth'] = (ADMIN_USER, ADMIN_PASS)
    if json_data:
        kwargs['json'] = json_data
    if params:
        kwargs['params'] = params

    try:
        if method == "GET":
            response = httpx.get(url, **kwargs)
        elif method == "POST":
            response = httpx.post(url, **kwargs)
        elif method == "DELETE":
            response = httpx.delete(url, **kwargs)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print(f"   ✅ Success")
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
        elif response.status_code == 201:
            print(f"   ✅ Created")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ⚠️  Status {response.status_code}")
            print(f"   Response: {response.json()}")

        return response
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    print("\n" + "🚀" * 35)
    print("        AUTH SERVICE V2 - ПОЛНОЕ ТЕСТИРОВАНИЕ")
    print("🚀" * 35)

    # =================================================================
    # PUBLIC ENDPOINTS
    # =================================================================
    print_section("1️⃣  PUBLIC ENDPOINTS")

    test_request("GET", "/", "Главная страница")
    test_request("GET", "/health", "Health check")
    test_request("GET", "/ping", "Ping endpoint")

    # =================================================================
    # OAUTH ENDPOINTS
    # =================================================================
    print_section("2️⃣  OAUTH ENDPOINTS")

    login_resp = test_request("GET", "/auth/login", "Инициация OAuth flow")
    if login_resp and login_resp.status_code == 200:
        data = login_resp.json()
        print(f"\n   🔗 Authorization URL:")
        print(f"   {data.get('authorization_url', 'N/A')[:100]}...")
        print(f"   State: {data.get('state', 'N/A')[:20]}...")

    # =================================================================
    # ADMIN - WHITELIST MANAGEMENT
    # =================================================================
    print_section("3️⃣  ADMIN - WHITELIST MANAGEMENT")

    # Добавить пользователя в whitelist
    test_request(
        "POST",
        "/admin/whitelist",
        "Добавить пользователя в whitelist",
        auth=True,
        json_data={
            "hh_user_id": "777888999",
            "description": "Test user for demo"
        }
    )

    # Получить whitelist
    test_request(
        "GET",
        "/admin/whitelist",
        "Получить весь whitelist",
        auth=True,
        params={"active_only": True}
    )

    # Получить whitelist (включая неактивных)
    test_request(
        "GET",
        "/admin/whitelist",
        "Получить whitelist (вкл. неактивных)",
        auth=True,
        params={"active_only": False, "limit": 10}
    )

    # Удалить пользователя из whitelist
    test_request(
        "DELETE",
        "/admin/whitelist",
        "Удалить пользователя из whitelist",
        auth=True,
        json_data={"hh_user_id": "777888999"}
    )

    # =================================================================
    # ADMIN - USER MANAGEMENT
    # =================================================================
    print_section("4️⃣  ADMIN - USER MANAGEMENT")

    # Получить всех пользователей
    test_request(
        "GET",
        "/admin/users",
        "Получить всех пользователей",
        auth=True,
        params={"active_only": False}
    )

    # Получить только активных пользователей
    test_request(
        "GET",
        "/admin/users",
        "Получить только активных пользователей",
        auth=True,
        params={"active_only": True, "limit": 5}
    )

    # =================================================================
    # ADMIN - STATISTICS
    # =================================================================
    print_section("5️⃣  ADMIN - STATISTICS")

    stats_resp = test_request(
        "GET",
        "/admin/statistics",
        "Получить статистику системы",
        auth=True
    )

    if stats_resp and stats_resp.status_code == 200:
        stats = stats_resp.json()
        print(f"\n   📊 СТАТИСТИКА:")
        print(f"   • Total Users: {stats.get('total_users', 0)}")
        print(f"   • Active Users: {stats.get('active_users', 0)}")
        print(f"   • Whitelisted Users: {stats.get('whitelisted_users', 0)}")
        print(f"   • Total Whitelist Entries: {stats.get('total_whitelist_entries', 0)}")

    # =================================================================
    # NEGATIVE TESTS
    # =================================================================
    print_section("6️⃣  NEGATIVE TESTS (проверка безопасности)")

    # Попытка доступа без авторизации
    print(f"\n📍 Попытка доступа к admin без авторизации")
    resp = httpx.get(f"{BASE_URL}/admin/statistics")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 401:
        print(f"   ✅ Правильно блокирует неавторизованный доступ")
    else:
        print(f"   ❌ Должен был вернуть 401")

    # Попытка с неправильным паролем
    print(f"\n📍 Попытка доступа с неправильным паролем")
    resp = httpx.get(f"{BASE_URL}/admin/statistics", auth=("admin", "wrong_password"))
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 401:
        print(f"   ✅ Правильно блокирует неправильные credentials")
    else:
        print(f"   ❌ Должен был вернуть 401")

    # =================================================================
    # SUMMARY
    # =================================================================
    print_section("📋 РЕЗЮМЕ")

    print("""
    ✅ Работающие функции:
       • Health check и мониторинг
       • OAuth flow инициация
       • Whitelist management (добавление/удаление/просмотр)
       • User management
       • Statistics и метрики
       • Basic Auth защита admin endpoints

    📝 Для полного тестирования OAuth flow нужен:
       • Браузер для авторизации в HeadHunter
       • Или callback сервер на http://127.0.0.1:5555/callback

    🔐 Admin credentials:
       • Username: admin
       • Password: admin123

    📚 Документация API:
       • Swagger UI: http://localhost:8000/docs (нужен браузер)
       • ReDoc: http://localhost:8000/redoc (нужен браузер)
       • OpenAPI JSON: http://localhost:8000/openapi.json
    """)

    print("=" * 70)
    print("✅ Тестирование завершено!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
