import json
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON файла'

    def handle(self, *args, **options):
        json_file = os.path.join('data', 'ingredients.json')

        if not os.path.exists(json_file):
            self.stdout.write(
                self.style.ERROR(f'Файл {json_file} не найден')
            )
            return

        try:
            with open(json_file, encoding='utf-8') as file:
                ingredients = json.load(file)

                created_count = 0
                existing_count = 0

                for ingredient in ingredients:
                    obj, created = Ingredient.objects.get_or_create(
                        name=ingredient['name'],
                        measurement_unit=ingredient['measurement_unit']
                    )
                    if created:
                        created_count += 1
                    else:
                        existing_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Загрузка завершена успешно!\n'
                        f'Создано новых ингредиентов: {created_count}\n'
                        f'Пропущено существующих: {existing_count}'
                    )
                )

        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR('Ошибка при чтении JSON файла')
            )
        except KeyError as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка в структуре данных: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Произошла ошибка: {str(e)}')
            )
