import os
import sys
import django
from django.core.management import call_command


def main():
    """
    Очищает базу данных, применяет миграции, загружает начальные данные
    и запускает сервер разработки Django.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram_back.settings')
    django.setup()

    # Очищаем базу данных
    print('Очистка базы данных...')
    try:
        call_command('clear_db')
        print('База данных успешно очищена')
    except Exception as e:
        print(f'Ошибка при очистке базы данных: {str(e)}')
        sys.exit(1)

    # Применяем миграции
    print('Применение миграций...')
    try:
        call_command('makemigrations')
        call_command('migrate')
        print('Миграции успешно применены')
    except Exception as e:
        print(f'Ошибка при применении миграций: {str(e)}')
        sys.exit(1)

    # Загружаем ингредиенты
    print('Загрузка ингредиентов...')
    try:
        call_command('load_ingredients')
        print('Ингредиенты успешно загружены')
    except Exception as e:
        print(f'Ошибка при загрузке ингредиентов: {str(e)}')
        sys.exit(1)

    # Запускаем сервер
    print('Запуск сервера разработки...')
    try:
        call_command('runserver', '0.0.0.0:8000')
    except KeyboardInterrupt:
        print('\nСервер остановлен')
    except Exception as e:
        print(f'Ошибка при запуске сервера: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
