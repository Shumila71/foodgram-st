from django.shortcuts import get_object_or_404, redirect

from .models import Recipe


def recipe_short_link(request, recipe_id):
    """
    Контроллер для реакции на короткую ссылку.
    Перенаправляет пользователя на полную страницу рецепта.
    """
    recipe = get_object_or_404(Recipe, id=recipe_id)
    return redirect(f'/recipes/{recipe.id}')
