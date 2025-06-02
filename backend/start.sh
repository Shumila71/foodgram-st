#!/bin/sh

# Ждем, пока база данных будет готова
echo "Waiting for postgres..."
sleep 5

# Собираем статические файлы
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Применяем миграции
echo "Applying migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Загружаем ингредиенты
echo "Loading ingredients data..."
python manage.py load_ingredients

# Запускаем сервер
echo "Starting Gunicorn..."
gunicorn foodgram_back.wsgi:application --bind 0.0.0.0:8000
