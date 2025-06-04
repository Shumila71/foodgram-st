from django.contrib import admin
from django.contrib.admin import display
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.db.models import Min, Max

from users.admin import BaseListFilter
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)


class OptimizedQuerysetMixin:
    """Миксин для оптимизации запросов."""

    def get_queryset(self, request):
        """Возвращает оптимизированный queryset."""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'user', 'recipe__author'
        )
        return queryset


class CookingTimeFilter(admin.SimpleListFilter):
    """Фильтр по времени готовки с динамическими порогами."""
    title = 'время готовки'
    parameter_name = 'cooking_time_range'

    def _get_time_thresholds(self):
        """Возвращает пороги времени для фильтрации."""
        time_stats = Recipe.objects.aggregate(
            min_time=Min('cooking_time'),
            max_time=Max('cooking_time')
        )

        min_time = time_stats['min_time']
        max_time = time_stats['max_time']

        if not min_time or not max_time:
            return None, None, None

        third = (max_time - min_time) // 3
        threshold1 = min_time + third
        threshold2 = min_time + 2 * third

        return threshold1, threshold2, (min_time, max_time)

    def lookups(self, request, model_admin):
        threshold1, threshold2, time_range = self._get_time_thresholds()

        if not threshold1 or (time_range[1] - time_range[0]) < 10:
            return []

        quick_count = Recipe.objects.filter(
            cooking_time__lte=threshold1).count()
        medium_count = Recipe.objects.filter(
            cooking_time__gt=threshold1, cooking_time__lte=threshold2).count()
        long_count = Recipe.objects.filter(cooking_time__gt=threshold2).count()

        return [
            ('quick', f'до {threshold1} мин ({quick_count})'),
            ('medium', f'{threshold1}-{threshold2} мин ({medium_count})'),
            ('long', f'больше {threshold2} мин ({long_count})'),
        ]

    def queryset(self, request, objects):
        threshold1, threshold2, _ = self._get_time_thresholds()

        if not threshold1:
            return objects

        if self.value() == 'quick':
            return objects.filter(cooking_time__lte=threshold1)
        if self.value() == 'medium':
            return objects.filter(
                cooking_time__gt=threshold1, cooking_time__lte=threshold2)
        if self.value() == 'long':
            return objects.filter(cooking_time__gt=threshold2)


class HasRecipesFilter(BaseListFilter):
    """Фильтр ингредиентов по наличию в рецептах."""
    title = 'есть в рецептах'
    parameter_name = 'has_recipes'
    filter_field = 'recipe_ingredients'


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для ингредиентов рецепта."""

    model = RecipeIngredient
    min_num = 1
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Административное представление рецептов."""

    list_display = (
        'id',
        'name',
        'cooking_time',
        'author',
        'favorites_count',
        'get_ingredients_display',
        'get_image_display'
    )
    search_fields = ('name', 'author__username')
    list_filter = (
        'author',
        CookingTimeFilter,
        'pub_date',
    )
    inlines = (RecipeIngredientInline,)

    @display(description='В избранном')
    def favorites_count(self, recipe):
        return recipe.favorite.count()

    @mark_safe
    @display(description='Ингредиенты')
    def get_ingredients_display(self, recipe):
        ingredients = recipe.recipe_ingredients.select_related('ingredient')

        return '<br>'.join([
            f'{ri.ingredient.name}'
            f' ({ri.amount}{ri.ingredient.measurement_unit})'
            for ri in ingredients
        ])

    @mark_safe
    @display(description='Изображение')
    def get_image_display(self, recipe):
        """Возвращает HTML-разметку для отображения изображения рецепта."""
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="50" height="50"'
            'style="border-radius: 8px; object-fit: cover;" />'
        return '<span style="color: #999;">Нет изображения</span>'

    def get_queryset(self, request):
        """Возвращает оптимизированный queryset для списка рецептов."""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'author'
        ).prefetch_related(
            'recipe_ingredients__ingredient',
            'favorite'
        )
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Административное представление ингредиентов."""

    list_display = ('name', 'measurement_unit', 'recipes_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = (
        'measurement_unit',
        HasRecipesFilter,
    )

    @display(description='В рецептах')
    def recipes_count(self, ingredient):
        """Возвращает количество рецептов с данным ингредиентом."""
        return ingredient.recipes_count

    def get_queryset(self, request):
        """Оптимизированный queryset с подсчетом рецептов."""
        return super().get_queryset(request).annotate(
            recipes_count=Count('recipe_ingredients', distinct=True)
        )


@admin.register(Favorite, ShoppingCart)
class FavoriteShoppingCartAdmin(admin.ModelAdmin, OptimizedQuerysetMixin):
    """Административное представление избранного и списка покупок."""

    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user__is_active', 'recipe__author')


admin.site.empty_value_display = '-пусто-'
