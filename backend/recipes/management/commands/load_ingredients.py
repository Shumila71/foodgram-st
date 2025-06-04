import json
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON файла'

    def handle(self, *args, **options):
        json_file = os.path.join('data', 'ingredients.json')

        try:
            with open(json_file, encoding='utf-8') as file:
                ingredients_data = json.load(file)

                existing_ingredients = set(Ingredient.objects.values_list(
                    'name', 'measurement_unit'))

                created_ingredients = Ingredient.objects.bulk_create(
                    [Ingredient(
                        **ingredient) for ingredient in ingredients_data
                        if (ingredient['name'],
                            ingredient['measurement_unit'])
                        not in existing_ingredients],
                    ignore_conflicts=True
                )
                created_count = len(created_ingredients)
                existing_count = len(ingredients_data) - created_count

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Загрузка завершена успешно!\n'
                        f'Создано новых ингредиентов: {created_count}\n'
                        f'Пропущено существующих: {existing_count}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    'Произошла ошибка '
                    f'при загрузке файла {json_file}: {e}'
                )
            )
