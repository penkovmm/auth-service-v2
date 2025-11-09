# Инструкция по интеграции auth-service-v2 с hh-resume-parser

## Обзор

`auth-service-v2` предоставляет централизованную OAuth 2.0 аутентификацию для HeadHunter API. Сервис управляет токенами доступа, их обновлением и сессиями пользователей.

## Архитектура интеграции

```
hh-resume-parser → auth-service-v2 → HeadHunter API
                   (получение токенов)
```

## Настройка auth-service-v2

### 1. Конфигурация

Создайте `.env` файл в `/home/penkovmm/services/auth-service-v2/`:

```bash
# Database
DATABASE_HOST=172.19.0.3
DATABASE_PORT=5432
DATABASE_NAME=auth_service
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password

# HeadHunter OAuth
HH_CLIENT_ID=your_client_id
HH_CLIENT_SECRET=your_client_secret
HH_REDIRECT_URI=http://127.0.0.1:5555/callback

# Security
ENCRYPTION_KEY=your_fernet_key  # generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ADMIN_USERNAME=admin
ADMIN_PASSWORD=hashed_password  # generate: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))"

# App settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 2. Запуск сервиса

```bash
cd /home/penkovmm/services/auth-service-v2
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Или используйте Docker Compose:

```bash
docker-compose up -d auth-service-v2
```

### 3. Создание whitelist

Добавьте разрешенных пользователей через admin API:

```bash
curl -X POST http://localhost:8000/admin/whitelist \
  -u admin:your_password \
  -H "Content-Type: application/json" \
  -d '{
    "hh_user_id": "123456789",
    "description": "Разработчик из команды"
  }'
```

## Интеграция с hh-resume-parser

### 1. Конфигурация hh-resume-parser

Обновите `.env` файл в `/home/penkovmm/projects/hh-resume-parser/`:

```bash
# Auth Service v2 settings
AUTH_SERVICE_URL=http://auth-service-v2:8000  # или http://localhost:8000
HH_SESSION_ID=your_session_id_here

# Fallback (устаревший метод, опционально)
HH_ACCESS_TOKEN=your_manual_token_here
```

### 2. Получение session_id

#### Способ 1: Через OAuth flow

1. Откройте в браузере: `http://localhost:8000/auth/login`
2. Скопируйте `authorization_url` из ответа
3. Перейдите по ссылке и авторизуйтесь в HeadHunter
4. После успешной авторизации получите `session_id` из ответа callback endpoint
5. Сохраните `session_id` в `.env` файл hh-resume-parser

#### Способ 2: Через curl (для тестирования)

```bash
# 1. Получить authorization URL
curl http://localhost:8000/auth/login | jq -r '.authorization_url'

# 2. Открыть URL в браузере и авторизоваться
# 3. Из callback URL извлечь code и state
# 4. Обменять code на токены и получить session_id
curl "http://localhost:8000/auth/callback?code=YOUR_CODE&state=YOUR_STATE"
```

### 3. Использование в коде

Модуль `shared/auth_utils.py` уже обновлен для работы с auth-service-v2:

```python
from shared.auth_utils import get_hh_access_token

# Получить токен используя session_id из .env
token = await get_hh_access_token()

# Или указать конкретный session_id
token = await get_hh_access_token(session_id="specific_session_id")

# Использовать токен для запросов к HH API
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Your App Name"
}
```

## API Endpoints

### Публичные endpoints

#### POST /auth/token
Получить валидный access token для HeadHunter API.

**Request:**
```json
{
  "session_id": "your_session_id"
}
```

**Response:**
```json
{
  "access_token": "hh_api_token",
  "expires_at": "2025-11-05T10:00:00Z",
  "user_id": 1
}
```

**Возможные ошибки:**
- `401` - Недействительная или истекшая сессия
- `500` - Внутренняя ошибка сервера

### Административные endpoints

Все admin endpoints требуют Basic Authentication (`-u admin:password`).

#### GET /admin/whitelist
Получить список разрешенных пользователей.

#### POST /admin/whitelist
Добавить пользователя в whitelist.

#### GET /admin/statistics
Получить статистику системы.

## Особенности работы

### Автоматическое обновление токенов

`auth-service-v2` автоматически обновляет access token при его истечении, используя refresh token. Клиенту не нужно беспокоиться об обновлении токенов.

### Fallback механизм

Если `auth-service-v2` недоступен или session_id не установлен, `get_hh_access_token()` автоматически использует `HH_ACCESS_TOKEN` из `.env` (устаревший метод).

### Безопасность

- Токены хранятся в БД в зашифрованном виде (Fernet encryption)
- Сессии имеют срок действия (по умолчанию 30 дней)
- Whitelist контролирует доступ к сервису
- Admin endpoints защищены Basic Auth

## Мониторинг

### Проверка здоровья сервиса

```bash
curl http://localhost:8000/health
```

### Просмотр логов

```bash
# Docker
docker-compose logs -f auth-service-v2

# Локально
tail -f /var/log/auth-service-v2.log
```

### Статистика

```bash
curl -u admin:password http://localhost:8000/admin/statistics
```

## Troubleshooting

### Ошибка: "Session not found"

**Причина:** session_id невалидный или истек.

**Решение:**
1. Проверьте правильность session_id в .env
2. Пройдите OAuth flow заново для получения нового session_id

### Ошибка: "User not authorized"

**Причина:** Пользователь не добавлен в whitelist.

**Решение:**
```bash
curl -X POST http://localhost:8000/admin/whitelist \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"hh_user_id": "USER_ID"}'
```

### Ошибка: "Unable to retrieve valid token"

**Причина:** Не удается обновить токен (refresh token истек).

**Решение:**
Пройдите OAuth flow заново для получения свежих токенов.

### Сервис использует fallback на HH_ACCESS_TOKEN

**Причина:** auth-service-v2 недоступен или session_id не настроен.

**Решение:**
1. Убедитесь что auth-service-v2 запущен: `curl http://localhost:8000/health`
2. Проверьте AUTH_SERVICE_URL в .env
3. Проверьте HH_SESSION_ID в .env

## Пример полного workflow

```bash
# 1. Запустить auth-service-v2
cd /home/penkovmm/services/auth-service-v2
docker-compose up -d

# 2. Добавить пользователя в whitelist
curl -X POST http://localhost:8000/admin/whitelist \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"hh_user_id": "YOUR_HH_USER_ID"}'

# 3. Получить session_id через OAuth
curl http://localhost:8000/auth/login
# Открыть authorization_url в браузере и авторизоваться
# Получить session_id из ответа

# 4. Настроить hh-resume-parser
echo "HH_SESSION_ID=obtained_session_id" >> /home/penkovmm/projects/hh-resume-parser/.env
echo "AUTH_SERVICE_URL=http://localhost:8000" >> /home/penkovmm/projects/hh-resume-parser/.env

# 5. Запустить hh-resume-parser
cd /home/penkovmm/projects/hh-resume-parser
docker-compose up -d
```

## Дополнительная информация

- **Документация API**: http://localhost:8000/docs
- **OpenAPI спецификация**: http://localhost:8000/openapi.json
- **Исходный код auth-service-v2**: `/home/penkovmm/services/auth-service-v2/`
- **Исходный код интеграции**: `/home/penkovmm/projects/hh-resume-parser/shared/auth_utils.py`
