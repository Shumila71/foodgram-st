import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from recipes.models import Recipe, Ingredient, RecipeIngredient

User = get_user_model()


class Command(BaseCommand):
    """По ТЗ обязательно наличие загрузки
    тестовых данных - пользователей и рецептов.
    Цитата из ТЗ:
    Иметь возможность подгрузить исходные данные:
    добавлять тестовых пользователей и рецепты.
    Веб-приложение должно быть наполнено тестовыми
    данными: нужно создать несколько пользователей
    с разными уровнями доступа и добавить хотя бы по
    одному рецепту от имени каждого пользователя.
    """
    help = 'Загружает тестовые данные пользователей и рецептов'

    def handle(self, *args, **options):
        self.load_users()
        self.load_recipes()

        self.stdout.write(
            self.style.SUCCESS(
                'Загрузка всех тестовых данных завершена успешно!')
        )

    def load_users(self):
        """Загружает пользователей из data/users.json"""
        try:
            with open('data/users.json', 'r', encoding='utf-8') as file:
                users_data = json.load(file)

            existing_emails = set(User.objects.values_list('email', flat=True))

            new_users = []
            for user_data in users_data:
                if user_data['email'] not in existing_emails:
                    new_users.append(User(**user_data))

            if new_users:
                for user in new_users:
                    user.set_password(user.password)
                User.objects.bulk_create(new_users)

            created_count = len(new_users)
            existing_count = len(users_data) - created_count

            self.stdout.write(
                self.style.SUCCESS(
                    f'Пользователи загружены:\n'
                    f'Создано новых: {created_count}\n'
                    f'Пропущено существующих: {existing_count}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    'Ошибка при загрузке пользователей'
                    f' из data/users.json: {str(e)}')
            )

    def load_recipes(self):
        """Загружает рецепты из data/recipes.json"""
        try:
            with open('data/recipes.json', 'r', encoding='utf-8') as file:
                recipes_data = json.load(file)

            with open('data/image.png', 'rb') as img_file:
                image_content = img_file.read()

            created_count = 0
            existing_count = 0

            for recipe_data in recipes_data:
                try:
                    author = User.objects.get(
                        email=recipe_data['author']['email'])
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Автор {recipe_data["author"]["email"]}'
                            'не найден, '
                            f'пропускаем рецепт {recipe_data["name"]}'
                        )
                    )
                    continue

                recipe, created = Recipe.objects.get_or_create(
                    name=recipe_data['name'],
                    author=author,
                    defaults={
                        'text': recipe_data['text'],
                        'cooking_time': recipe_data['cooking_time']
                    }
                )

                if created:
                    image_name = f"recipe_{recipe.id}.png"
                    recipe.image.save(
                        image_name,
                        ContentFile(image_content),
                        save=True
                    )

                    recipe_ingredients = []
                    for ingredient_data in recipe_data['ingredients']:
                        try:
                            ingredient = Ingredient.objects.get(
                                id=ingredient_data['id'])
                            recipe_ingredients.append(
                                RecipeIngredient(
                                    recipe=recipe,
                                    ingredient=ingredient,
                                    amount=ingredient_data['amount']
                                )
                            )
                        except Ingredient.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Ингредиент {ingredient_data["id"]}'
                                    'не найден '
                                    f'для рецепта {recipe_data["name"]}'
                                )
                            )

                    if recipe_ingredients:
                        RecipeIngredient.objects.bulk_create(
                            recipe_ingredients)

                    created_count += 1
                else:
                    existing_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Рецепты загружены:\n'
                    f'Создано новых: {created_count}\n'
                    f'Пропущено существующих: {existing_count}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    'Ошибка при загрузке'
                    f'рецептов из data/recipes.json: {str(e)}')
            )
