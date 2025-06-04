from django.shortcuts import redirect
from django.http import Http404

from .models import Recipe


def recipe_short_link(request, recipe_id):
    """
    Контроллер для реакции на короткую ссылку.
    Перенаправляет пользователя на полную страницу рецепта.
    """
    if not Recipe.objects.filter(id=recipe_id).exists():
        raise Http404
    return redirect(f'/recipes/{recipe_id}')
