# HH Auth Service v2.0

Современный микросервис для OAuth 2.0 авторизации через HeadHunter API.

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

## Описание

Auth Service v2 - это независимый микросервис, который:
- 🔐 Управляет OAuth 2.0 flow с HeadHunter
- 🔄 Хранит и автоматически обновляет токены пользователей
- 🌐 Предоставляет REST API для других микросервисов
- ✅ Контролирует доступ через whitelist пользователей
- 🔒 Обеспечивает безопасное хранение токенов с шифрованием (Fernet)
- 📊 Audit logging всех важных событий
- 🚀 Async/await для высокой производительности

## Технологии

- **Backend**: Python 3.12, FastAPI 0.104+ (async)
- **Database**: PostgreSQL 17
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **HTTP Client**: httpx (async)
- **Security**: cryptography (Fernet encryption), bcrypt
- **Logging**: structlog (JSON)
- **Rate Limiting**: slowapi
- **Server**: Uvicorn (ASGI)
- **Containerization**: Docker, Docker Compose

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env файл
```

### 3. Применение миграций

```bash
alembic upgrade head
```

### 4. Запуск сервера

```bash
uvicorn app.main:app --reload --port 8000
```

## Docker

### Быстрый запуск

1. **Скопируйте и настройте переменные окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл, заполните HH_CLIENT_ID, HH_CLIENT_SECRET, ENCRYPTION_KEY
```

2. **Запустите сервисы:**
```bash
docker-compose up -d
```

3. **Проверьте статус:**
```bash
docker-compose ps
curl http://localhost:8000/health
```

4. **Просмотр логов:**
```bash
docker-compose logs -f auth-service
```

### Отдельная сборка и запуск

```bash
# Сборка образа
docker build -t auth-service-v2 .

# Запуск контейнера
docker run -d \
  --name auth-service \
  -p 8000:8000 \
  --env-file .env \
  auth-service-v2
```

### Полезные команды

```bash
# Остановка сервисов
docker-compose down

# Пересборка после изменений
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Выполнение миграций вручную
docker-compose exec auth-service alembic upgrade head

# Доступ к базе данных
docker-compose exec postgres psql -U authuser -d auth_service
```

## API Endpoints

### OAuth Flow
- `GET /auth/login` - Инициация авторизации
- `GET /auth/callback` - OAuth callback
- `POST /auth/exchange` - Обмен кода на сессию
- `POST /auth/token` - Получение HH access token
- `POST /auth/refresh` - Принудительный refresh токена
- `POST /auth/logout` - Завершение сессии

### Users
- `GET /users/me` - Информация о текущем пользователе

### Admin (Basic Auth)
- `POST /admin/users/allow` - Добавить пользователя в whitelist
- `DELETE /admin/users/{hh_user_id}` - Удалить из whitelist
- `GET /admin/users` - Список разрешенных пользователей
- `GET /admin/sessions` - Активные сессии
- `DELETE /admin/sessions/{session_id}` - Завершить сессию
- `GET /admin/audit-log` - Лог аудита

### Health
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Документация

### Автоматическая API документация

После запуска доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Подробная документация

- **[OAuth Flow](docs/OAUTH_FLOW.md)** - Детальное описание OAuth 2.0 flow с диаграммами и примерами
- **[API Examples](docs/API_EXAMPLES.md)** - Примеры использования API на Python, JavaScript и других языках
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Руководство администратора: управление пользователями, сессиями, мониторинг
- **[Architecture](docs/ARCHITECTURE.md)** - Архитектура системы, диаграммы компонентов, технический стек
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Полный чеклист для production deployment

## Структура проекта

```
auth_service_v2/
├── app/
│   ├── api/              # API endpoints
│   │   └── routes/       # Роутеры (oauth, admin, health)
│   ├── core/             # Конфигурация и утилиты
│   ├── db/               # Модели и репозитории
│   │   ├── models.py     # SQLAlchemy модели
│   │   └── repositories/ # Репозитории для доступа к данным
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   └── main.py           # FastAPI приложение
├── docs/                 # Документация
│   ├── OAUTH_FLOW.md     # OAuth flow documentation
│   ├── API_EXAMPLES.md   # API usage examples
│   ├── ADMIN_GUIDE.md    # Administrator guide
│   ├── ARCHITECTURE.md   # System architecture
│   └── DEPLOYMENT_CHECKLIST.md  # Deployment guide
├── tests/                # Тесты
├── alembic/              # Миграции БД
├── templates/            # HTML шаблоны
├── Dockerfile            # Docker образ
├── docker-compose.yml    # Docker Compose конфигурация
└── requirements.txt      # Python зависимости
```

## Разработка

### Создание миграции

```bash
alembic revision --autogenerate -m "описание изменений"
```

### Запуск тестов

```bash
pytest
```

### Запуск тестов с покрытием

```bash
pytest --cov=app --cov-report=html
```

## Безопасность

⚠️ **Важно:**
- Храните `.env` файл в секрете
- Используйте сильные пароли для БД и админа
- Регулярно ротируйте `ENCRYPTION_KEY`
- Логи НЕ содержат токены и секреты

## Лицензия

Proprietary - для внутреннего использования

## Контакты

- Email: penkovmm@gmail.com
- GitHub: https://github.com/penkovmm/auth_service_v2

## Production Deployment

📋 **Полный чеклист для production deployment:** [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)

### Требования

- Docker и Docker Compose
- PostgreSQL 17 (или используйте контейнер из docker-compose)
- Минимум 2 GB RAM (рекомендуется 4 GB)
- SSL сертификат (для HTTPS)

### Настройка для production

1. **Обновите .env файл:**
   - Установите `ENVIRONMENT=production`
   - Установите `DEBUG=false`
   - Используйте сильные пароли для `POSTGRES_PASSWORD` и `ADMIN_PASSWORD`
   - Настройте `HH_REDIRECT_URI` на ваш production домен

2. **Генерация секретов:**
```bash
# Encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Admin password hash
python -c "import bcrypt; print(bcrypt.hashpw('your_password'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))"
```

3. **Запуск с ограничениями ресурсов:**
```bash
docker-compose up -d
```

### Мониторинг

- Health check: `GET /health`
- Logs: `docker-compose logs -f auth-service`
- Database backup: `docker-compose exec postgres pg_dump -U authuser auth_service > backup.sql`

### Обновление

```bash
# 1. Остановка сервиса
docker-compose stop auth-service

# 2. Обновление кода
git pull

# 3. Пересборка образа
docker-compose build auth-service

# 4. Применение миграций
docker-compose run --rm auth-service alembic upgrade head

# 5. Запуск нового контейнера
docker-compose up -d auth-service
```

## Безопасность

- ✅ Все токены шифруются Fernet (симметричное шифрование)
- ✅ Пароли хешируются с bcrypt
- ✅ CSRF protection для OAuth flow (state validation)
- ✅ Whitelist авторизованных пользователей
- ✅ Sensitive data фильтруется в логах
- ✅ Basic Auth для admin endpoints
- ✅ Автоматическое истечение сессий
- ✅ Audit logging всех важных событий

## Лицензия

Proprietary

