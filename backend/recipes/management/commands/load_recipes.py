import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from recipes.models import Recipe, Ingredient, RecipeIngredient
from django.core.files.base import ContentFile

User = get_user_model()


class Command(BaseCommand):
    help = 'Load test recipes data'

    def handle(self, *args, **options):
        try:
            with open('data/recipes.json', 'r', encoding='utf-8') as file:
                recipes_data = json.load(file)

            with open('data/image.png', 'rb') as img_file:
                image_content = img_file.read()

            for recipe_data in recipes_data:
                try:
                    author = User.objects.get(
                        email=recipe_data['author']['email']
                    )
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'{recipe_data["author"]["email"]} нету,'
                            f'skipping recipe {recipe_data["name"]}'
                        )
                    )
                    continue

                if not Recipe.objects.filter(
                        name=recipe_data['name'],
                        author=author).exists():
                    recipe = Recipe.objects.create(
                        name=recipe_data['name'],
                        text=recipe_data['text'],
                        cooking_time=recipe_data['cooking_time'],
                        author=author
                    )

                    image_name = f"recipe_{recipe.id}.png"
                    recipe.image.save(
                        image_name,
                        ContentFile(image_content),
                        save=True
                    )

                    for ingredient_data in recipe_data['ingredients']:
                        try:
                            ingredient = Ingredient.objects.get(
                                id=ingredient_data['id']
                            )
                            RecipeIngredient.objects.create(
                                recipe=recipe,
                                ingredient=ingredient,
                                amount=ingredient_data['amount']
                            )
                        except Ingredient.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Ingredient {ingredient_data["id"]} '
                                    f'not found for {recipe_data["name"]}'
                                )
                            )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created recipe {recipe_data["name"]}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'рецепт {recipe_data["name"]} у {author.username}'
                            'уже есть'
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS('Successfully loaded all recipes')
            )

        except FileNotFoundError as e:
            self.stdout.write(
                self.style.ERROR(
                    f'File not found: {str(e)}. '
                    'Please make sure all required files exist.'
                )
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(
                    'Invalid JSON format in data/recipes.json'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading recipes: {str(e)}')
            )
