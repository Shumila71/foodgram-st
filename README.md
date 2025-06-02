# Foodgram - Продуктовый помощник

Foodgram - это веб-приложение, в котором пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

## Предварительные требования

- Docker
- Docker Compose

## Запуск проекта

1. Клонируйте репозиторий:
```bash
git clone <your-repository-url>
cd foodgram-st
```

2. Запустите проект с помощью Docker Compose:
```bash
docker compose up --build
```
Для запуска в фоновом режиме добавьте флаг `-d`:
```bash
docker compose up -d --build
```

> **Важно**: После запуска контейнеров нужно подождать 30-50 секунд, пока все сервисы полностью не инициализируются.

3. Загрузите тестовые данные (выполняйте команды строго в указанном порядке):
```bash
# Создание пользователей
docker compose exec backend python manage.py load_users

# Создание рецептов
docker compose exec backend python manage.py load_recipes
```

4. Создайте суперпользователя для доступа к админ-панели:
```bash
docker compose exec backend python manage.py createsuperuser
```

После выполнения этих шагов приложение будет доступно по адресу: http://localhost

Документация API: http://localhost/api/docs/

## Структура проекта

### Бэкенд (/backend)
- `foodgram_back/` - основной проект Django
- `api/` - приложение с API endpoints
- `recipes/` - приложение для работы с рецептами
- `users/` - приложение для работы с пользователями
- `data/` - тестовые данные (пользователи, рецепты)

### Фронтенд (/frontend)
- React-приложение
- Собирается при запуске контейнера

### Инфраструктура
- `nginx/` - конфигурация Nginx
- `docker-compose.yml` - описание сервисов (backend, frontend, db, nginx)
- `.env` - переменные окружения (создайте на основе .env.example)

## API Documentation

Подробная документация API доступна по адресу http://localhost/api/docs/ после запуска проекта.

## Технологии

- **Backend**: Django REST Framework
- **Frontend**: React
- **Database**: PostgreSQL
- **Web Server**: Nginx
- **Containerization**: Docker & Docker Compose