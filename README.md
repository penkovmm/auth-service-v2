# HH Auth Service v2.0

Современный микросервис для OAuth 2.0 авторизации через HeadHunter API.

## Описание

Auth Service v2 - это независимый микросервис, который:
- Управляет OAuth 2.0 flow с HeadHunter
- Хранит и автоматически обновляет токены пользователей
- Предоставляет API для других микросервисов
- Контролирует доступ через whitelist пользователей
- Обеспечивает безопасное хранение токенов с шифрованием

## Технологии

- **Backend**: Python 3.11+, FastAPI (async)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **HTTP Client**: httpx (async)
- **Security**: cryptography (Fernet encryption)
- **Logging**: structlog (JSON)
- **Rate Limiting**: slowapi

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

### Сборка образа

```bash
docker build -t auth-service-v2 .
```

### Запуск с docker-compose

```bash
docker-compose up -d
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

## Документация API

После запуска доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Структура проекта

```
auth_service_v2/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Конфигурация и утилиты
│   ├── db/               # Модели и репозитории
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   └── main.py           # FastAPI приложение
├── tests/                # Тесты
├── alembic/              # Миграции БД
├── templates/            # HTML шаблоны
└── docker/               # Docker конфигурация
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
