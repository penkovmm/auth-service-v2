# Auth Service v2 - Руководство по тестированию без браузера

## 🚀 Быстрый старт

### Проверка работоспособности
```bash
# Health check
curl http://localhost:8000/health | jq

# Ping
curl http://localhost:8000/ping | jq

# Главная
curl http://localhost:8000/ | jq
```

## 🔐 Admin API (требует авторизации)

### Whitelist Management

**Добавить пользователя в whitelist:**
```bash
curl -u admin:admin123 \
  -X POST http://localhost:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d '{
    "hh_user_id": "12345678",
    "description": "My test user"
  }' | jq
```

**Получить whitelist:**
```bash
# Все активные
curl -u admin:admin123 \
  "http://localhost:8000/admin/whitelist?active_only=true" | jq

# Все (включая неактивных)
curl -u admin:admin123 \
  "http://localhost:8000/admin/whitelist?active_only=false" | jq

# С ограничением
curl -u admin:admin123 \
  "http://localhost:8000/admin/whitelist?active_only=true&limit=10" | jq
```

**Удалить пользователя из whitelist:**
```bash
curl -u admin:admin123 \
  -X DELETE http://localhost:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d '{"hh_user_id": "12345678"}' | jq
```

### User Management

**Получить всех пользователей:**
```bash
curl -u admin:admin123 \
  "http://localhost:8000/admin/users?active_only=false" | jq
```

**Получить только активных:**
```bash
curl -u admin:admin123 \
  "http://localhost:8000/admin/users?active_only=true&limit=5" | jq
```

**Получить audit logs пользователя:**
```bash
curl -u admin:admin123 \
  "http://localhost:8000/admin/users/1/audit?limit=50" | jq
```

### Statistics

**Получить статистику:**
```bash
curl -u admin:admin123 http://localhost:8000/admin/statistics | jq
```

## 🔄 OAuth Flow

**Шаг 1: Получить URL для авторизации**
```bash
curl http://localhost:8000/auth/login | jq
```

Ответ:
```json
{
  "authorization_url": "https://hh.ru/oauth/authorize?...",
  "state": "random_state_string"
}
```

**Шаг 2: Авторизация (через браузер или туннель)**

Для полного тестирования OAuth без браузера, можно использовать SSH туннель:

```bash
# На локальной машине (с браузером)
ssh -L 8000:localhost:8000 penkovmm@your-server

# Теперь можно открыть в браузере:
# http://localhost:8000/auth/login
```

## 📊 Мониторинг

**Просмотр OpenAPI схемы:**
```bash
curl http://localhost:8000/openapi.json | jq > openapi.json
```

**Проверка версии:**
```bash
curl http://localhost:8000/ | jq '.version'
```

## 🧪 Python скрипты для тестирования

### 1. Базовый тест (уже создан)
```bash
python test_api.py
```

### 2. Полный тест всех endpoints (уже создан)
```bash
python test_all_endpoints.py
```

### 3. Интерактивный тест
```python
import httpx

BASE = "http://localhost:8000"
AUTH = ("admin", "admin123")

# Добавить пользователя
resp = httpx.post(
    f"{BASE}/admin/whitelist",
    json={"hh_user_id": "999", "description": "Test"},
    auth=AUTH
)
print(resp.json())

# Получить список
resp = httpx.get(f"{BASE}/admin/whitelist", auth=AUTH)
print(resp.json())

# Статистика
resp = httpx.get(f"{BASE}/admin/statistics", auth=AUTH)
print(resp.json())
```

## 🔍 Полезные команды

**Проверка логов в реальном времени:**
```bash
# Если запущен через uvicorn в фоне
tail -f /tmp/auth-service.log

# Если через docker-compose
docker-compose logs -f auth-service
```

**Проверка процессов:**
```bash
ps aux | grep uvicorn
netstat -tlnp | grep 8000
```

**Проверка базы данных:**
```bash
docker exec test-app-postgres psql -U testuser -d auth_service -c "
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'public';
"
```

**Количество записей в таблицах:**
```bash
docker exec test-app-postgres psql -U testuser -d auth_service -c "
  SELECT
    'users' as table_name, COUNT(*) FROM users
  UNION ALL
  SELECT 'allowed_users', COUNT(*) FROM allowed_users
  UNION ALL
  SELECT 'oauth_tokens', COUNT(*) FROM oauth_tokens;
"
```

## 🐛 Отладка

**Проверка credentials:**
```bash
# Должен вернуть 401
curl http://localhost:8000/admin/statistics

# Должен вернуть 401
curl -u admin:wrong_password http://localhost:8000/admin/statistics

# Должен работать
curl -u admin:admin123 http://localhost:8000/admin/statistics
```

**Тест производительности:**
```bash
# 10 запросов подряд
for i in {1..10}; do
  time curl -s http://localhost:8000/health > /dev/null
done
```

**Проверка CORS (если включен):**
```bash
curl -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/health -v
```

## 📝 Примеры реальных сценариев

### Сценарий 1: Добавление нового пользователя
```bash
#!/bin/bash
HH_USER_ID="174714255"

# 1. Проверить, есть ли уже в whitelist
echo "Checking whitelist..."
curl -s -u admin:admin123 http://localhost:8000/admin/whitelist | \
  jq ".allowed_users[] | select(.hh_user_id == \"$HH_USER_ID\")"

# 2. Добавить если нет
echo "Adding to whitelist..."
curl -u admin:admin123 \
  -X POST http://localhost:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d "{\"hh_user_id\": \"$HH_USER_ID\", \"description\": \"Production user\"}" | jq

# 3. Проверить статистику
echo "Checking statistics..."
curl -s -u admin:admin123 http://localhost:8000/admin/statistics | jq
```

### Сценарий 2: Мониторинг системы
```bash
#!/bin/bash
while true; do
  clear
  echo "=== AUTH SERVICE MONITORING ==="
  echo "Time: $(date)"
  echo ""

  # Health
  echo "Health:"
  curl -s http://localhost:8000/health | jq -r '.status, .database'
  echo ""

  # Stats
  echo "Statistics:"
  curl -s -u admin:admin123 http://localhost:8000/admin/statistics | \
    jq -r '"Users: \(.total_users), Whitelist: \(.whitelisted_users)"'

  sleep 5
done
```

## 🎯 Что можно протестировать БЕЗ браузера:

✅ Health check и мониторинг
✅ Admin API (whitelist, users, statistics)
✅ OAuth URL generation
✅ Security (auth/authorization)
✅ Database connectivity
✅ API performance

❌ Что нужен браузер:
- Полный OAuth flow (авторизация в HeadHunter)
- UI тестирование

## 🌐 Доступ с другой машины

Если хотите тестировать с локальной машины (где есть браузер):

**Вариант 1: SSH туннель**
```bash
ssh -L 8000:localhost:8000 penkovmm@your-server-ip
# Теперь на локальной машине: http://localhost:8000
```

**Вариант 2: Открыть порт (не рекомендуется для production)**
```bash
# Изменить в .env:
HOST=0.0.0.0

# Теперь доступен: http://your-server-ip:8000
```

---

**Credentials:**
- Username: `admin`
- Password: `admin123`

**Endpoints:**
- Service: http://localhost:8000
- Health: http://localhost:8000/health
- Stats: http://localhost:8000/admin/statistics (auth required)
