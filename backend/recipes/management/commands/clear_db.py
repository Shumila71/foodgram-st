from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Очищает все таблицы в базе данных'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            all_models = apps.get_models()

            if connection.vendor == 'postgresql':
                cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
            elif connection.vendor == 'sqlite':
                cursor.execute('PRAGMA foreign_keys=OFF;')

            for model in all_models:
                try:
                    model.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Успешно очищена таблица {model._meta.db_table}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            'Ошибка при очистке таблицы '
                            f'{model._meta.db_table}: {str(e)}'
                        )
                    )

            if connection.vendor == 'postgresql':
                cursor.execute('SET CONSTRAINTS ALL IMMEDIATE;')
            elif connection.vendor == 'sqlite':
                cursor.execute('PRAGMA foreign_keys=ON;')

        self.stdout.write(
            self.style.SUCCESS('База данных успешно очищена')
        )
