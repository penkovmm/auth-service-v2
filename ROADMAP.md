# Roadmap - Auth Service v2.0

## ✅ Выполнено (2025-11-03)

### Этап 0: Инициализация проекта
- [x] Создана полная структура проекта
- [x] Инициализирован git репозиторий
- [x] Создан .gitignore
- [x] Создан README.md с документацией
- [x] Создан requirements.txt с зависимостями
- [x] Создан .env.example (шаблон)
- [x] Создан .env с реальными данными
- [x] Сделан первый commit

**Конфигурация:**
- Проект: `/home/penkovmm/auth_service_v2/`
- Git: Инициализирован, коммит `75ee168`
- HH OAuth: Client ID, Secret, App Token настроены
- Encryption Key: Сгенерирован и настроен
- Whitelist: User ID 174714255 (penkovmm)

---

## 📋 План работ на следующий этап

### Этап 1: Core Infrastructure (2-3 часа)

#### 1.1 app/core/config.py
**Задача:** Настройка Pydantic Settings
```python
class Settings(BaseSettings):
    # Application
    app_name: str
    app_version: str
    environment: str
    debug: bool

    # Database
    database_url: str

    # HH OAuth
    hh_client_id: str
    hh_client_secret: str
    # ... и т.д.
```

**Критерии готовности:**
- [ ] Все переменные из .env загружаются
- [ ] Валидация через Pydantic
- [ ] Singleton instance настроек
- [ ] Type hints на всех полях

---

#### 1.2 app/core/security.py
**Задача:** Encryption/Decryption токенов, Basic Auth

```python
class SecurityService:
    def encrypt_token(self, token: str) -> str
    def decrypt_token(self, encrypted: str) -> str
    def verify_basic_auth(self, credentials: HTTPBasicCredentials) -> bool
    def hash_password(self, password: str) -> str
```

**Критерии готовности:**
- [ ] Fernet encryption работает
- [ ] Decrypt возвращает оригинальный токен
- [ ] Basic Auth проверка
- [ ] Тесты на encryption/decryption (100% coverage)

---

#### 1.3 app/core/logging.py
**Задача:** Structured logging с structlog

```python
def setup_logging(log_level: str, log_format: str):
    # Настройка structlog
    # JSON формат
    # Фильтрация токенов
```

**Критерии готовности:**
- [ ] JSON формат логов
- [ ] Уровни логирования (DEBUG, INFO, WARNING, ERROR)
- [ ] Контекстные поля (user_id, request_id)
- [ ] НЕ логируются токены, ключи, пароли

---

### Этап 2: Database Layer (2-3 часа)

#### 2.1 app/db/database.py
**Задача:** Async SQLAlchemy engine и session

```python
async_engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(async_engine)

async def get_db() -> AsyncSession:
    # Dependency для FastAPI
```

**Критерии готовности:**
- [ ] Async engine создается
- [ ] Connection pool настроен
- [ ] get_db() dependency работает
- [ ] Graceful shutdown

---

#### 2.2 app/db/models.py
**Задача:** SQLAlchemy ORM модели (7 таблиц)

**Таблицы:**
1. `users` - Пользователи
2. `user_sessions` - Сессии
3. `oauth_tokens` - HH токены (encrypted)
4. `oauth_exchange_codes` - One-time codes
5. `oauth_states` - OAuth states для CSRF
6. `allowed_users` - Whitelist
7. `audit_log` - Логи аудита

**Критерии готовности:**
- [ ] Все 7 таблиц определены
- [ ] Связи между таблицами (ForeignKey)
- [ ] Индексы на важных полях
- [ ] created_at, updated_at timestamps

---

#### 2.3 app/db/repositories/
**Задача:** Repository pattern для каждой сущности

**Файлы:**
- `user_repository.py` - CRUD для users
- `session_repository.py` - Управление сессиями
- `token_repository.py` - OAuth токены
- `audit_repository.py` - Audit log

**Пример:**
```python
class UserRepository:
    async def create(self, user_data: dict) -> User
    async def get_by_id(self, user_id: int) -> User | None
    async def get_by_hh_user_id(self, hh_user_id: str) -> User | None
    async def is_whitelisted(self, hh_user_id: str) -> bool
```

**Критерии готовности:**
- [ ] Все CRUD операции реализованы
- [ ] Async методы
- [ ] Type hints
- [ ] Обработка ошибок

---

### Этап 3: Alembic Migrations (1 час)

#### 3.1 Настройка Alembic
```bash
alembic init alembic
```

**Задачи:**
- [ ] alembic.ini настроен
- [ ] alembic/env.py настроен для async
- [ ] Подключение к models

---

#### 3.2 Создание первой миграции
```bash
alembic revision --autogenerate -m "Initial schema"
```

**Критерии готовности:**
- [ ] Миграция создает все 7 таблиц
- [ ] Индексы создаются
- [ ] alembic upgrade head работает
- [ ] alembic downgrade работает

---

#### 3.3 Initial Data
**Задача:** Добавить начальные данные

```sql
-- В миграции или отдельном скрипте
INSERT INTO allowed_users (hh_user_id, email, notes, added_by)
VALUES ('174714255', 'penkovmm@gmail.com', 'Project owner', 'system');
```

---

### Этап 4: Services Layer (3-4 часа)

#### 4.1 app/services/hh_oauth_service.py
**Задача:** OAuth flow с HeadHunter

```python
class HHOAuthService:
    async def generate_auth_url(self, state: str) -> str
    async def exchange_code_for_tokens(self, code: str) -> dict
    async def refresh_access_token(self, refresh_token: str) -> dict
    async def get_user_info(self, access_token: str) -> dict
```

**Критерии готовности:**
- [ ] httpx async client
- [ ] Обработка ошибок HH API
- [ ] Retry логика
- [ ] Логирование (БЕЗ токенов)

---

#### 4.2 app/services/token_service.py
**Задача:** Управление токенами

```python
class TokenService:
    async def save_tokens(self, user_id: int, access_token: str, refresh_token: str, expires_in: int)
    async def get_valid_token(self, user_id: int) -> str
    async def is_token_expired(self, user_id: int) -> bool
    async def refresh_if_needed(self, user_id: int) -> str
```

**Критерии готовности:**
- [ ] Токены шифруются перед сохранением
- [ ] Автоматический refresh при истечении
- [ ] Кеширование (опционально)

---

#### 4.3 app/services/session_service.py
**Задача:** Управление сессиями

```python
class SessionService:
    async def create_session(self, user_id: int, ip: str, user_agent: str) -> UUID
    async def get_session(self, session_id: UUID) -> Session | None
    async def is_session_valid(self, session_id: UUID) -> bool
    async def delete_session(self, session_id: UUID)
    async def cleanup_expired_sessions()
```

---

#### 4.4 app/services/admin_service.py
**Задача:** Админские операции

```python
class AdminService:
    async def add_to_whitelist(self, hh_user_id: str, email: str, notes: str)
    async def remove_from_whitelist(self, hh_user_id: str)
    async def get_all_users()
    async def get_active_sessions()
    async def kill_session(self, session_id: UUID)
```

---

### Этап 5: API Routes (3-4 часа)

#### 5.1 app/api/dependencies.py
**Задача:** FastAPI dependencies

```python
async def get_db() -> AsyncSession
async def get_current_session(session_id: str) -> Session
async def verify_admin(credentials: HTTPBasicCredentials)
```

---

#### 5.2 app/api/routes/auth.py
**Endpoints:**
- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/exchange`
- `POST /auth/token`
- `POST /auth/refresh`
- `POST /auth/logout`

**Критерии готовности:**
- [ ] Все endpoints реализованы
- [ ] Валидация через Pydantic
- [ ] Обработка ошибок
- [ ] Документация в docstrings

---

#### 5.3 app/api/routes/users.py
**Endpoints:**
- `GET /users/me`

---

#### 5.4 app/api/routes/admin.py
**Endpoints:**
- `POST /admin/users/allow`
- `DELETE /admin/users/{hh_user_id}`
- `GET /admin/users`
- `GET /admin/sessions`
- `DELETE /admin/sessions/{session_id}`
- `GET /admin/audit-log`

**Зависимость:** Basic Auth через dependency

---

#### 5.5 app/api/routes/health.py
**Endpoints:**
- `GET /health`
- `GET /metrics`

---

### Этап 6: Schemas (1-2 часа)

#### Создать Pydantic схемы для всех endpoints

**Файлы:**
- `app/schemas/auth.py`
- `app/schemas/user.py`
- `app/schemas/admin.py`
- `app/schemas/common.py`

---

### Этап 7: Main Application (1 час)

#### 7.1 app/main.py
**Задача:** FastAPI app setup

```python
app = FastAPI(
    title="HH Auth Service v2",
    version="2.0.0"
)

# Middleware
app.add_middleware(CORSMiddleware)
# Rate limiting
# Logging

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(health_router)

# Startup/Shutdown events
@app.on_event("startup")
async def startup():
    # Create DB tables
    # Start cleanup tasks

@app.on_event("shutdown")
async def shutdown():
    # Close DB connections
```

---

### Этап 8: HTML Templates (1 час)

#### Создать простые HTML страницы

**Файлы:**
- `templates/login.html` - Страница входа с кнопкой "Войти через HH"
- `templates/success.html` - Успешная авторизация, показать session_id
- `templates/error.html` - Ошибка авторизации

---

### Этап 9: Testing (3-4 часа)

#### 9.1 tests/conftest.py
**Задача:** Pytest fixtures

```python
@pytest.fixture
async def db_session():
    # Test database session

@pytest.fixture
async def test_client():
    # FastAPI test client
```

---

#### 9.2 Unit Tests
- `tests/test_security.py` - Encryption/decryption
- `tests/test_services.py` - Все сервисы
- `tests/test_repositories.py` - CRUD операции

---

#### 9.3 Integration Tests
- `tests/test_oauth_flow.py` - Полный OAuth цикл (mock HH API)
- `tests/test_admin_api.py` - Admin endpoints
- `tests/test_token_refresh.py` - Автоматический refresh

---

### Этап 10: Docker & Deployment (2-3 часа)

#### 10.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

#### 10.2 docker-compose.yml
```yaml
services:
  auth_service_v2:
    build: .
    ports:
      - "5555:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
    depends_on:
      - postgres
```

---

#### 10.3 Интеграция с основным проектом
**Задача:** Обновить `/home/penkovmm/hh-resume-parser/docker-compose.yml`

Добавить auth_service_v2 в существующий compose

---

## 📊 Прогресс

**Всего этапов:** 10
**Выполнено:** 1 (Этап 0: Инициализация)
**Осталось:** 9

**Примерное время:** ~23 часа

---

## 🎯 Следующая сессия

Начнем с **Этапа 1: Core Infrastructure**

**Первые задачи:**
1. Реализовать `app/core/config.py`
2. Реализовать `app/core/security.py`
3. Реализовать `app/core/logging.py`
4. Написать тесты для encryption/decryption

**Ожидаемое время:** 2-3 часа

---

## 📝 Полезные команды

```bash
# Переход в проект
cd /home/penkovmm/auth_service_v2

# Установка зависимостей (когда начнем)
pip install -r requirements.txt

# Запуск сервера (когда будет готово)
uvicorn app.main:app --reload --port 8000

# Миграции
alembic upgrade head
alembic revision --autogenerate -m "описание"

# Тесты
pytest
pytest --cov=app

# Git
git status
git add .
git commit -m "описание"
git log --oneline
```

---

## 🔗 Ссылки

- **ТЗ:** См. сообщение выше (600+ строк)
- **Проект:** `/home/penkovmm/auth_service_v2/`
- **Старый сервис:** `/home/penkovmm/hh-resume-parser/auth_service_hh/`
- **Git:** Локальный репозиторий (можно потом push на GitHub)

---

## ⚠️ Важные замечания

1. **Не забыть:** После установки passlib сгенерировать хеш пароля для админа
2. **DNS:** Настроить `hh.penkovmm.ru` когда будем деплоить в продакшен
3. **HH Redirect URI:** Обновить в настройках HH OAuth при переходе на домен
4. **Encryption Key:** Хранить в безопасности, не коммитить в git
5. **PostgreSQL:** Создать БД `auth_service` перед первым запуском

---

_Документ обновлен: 2025-11-03_
