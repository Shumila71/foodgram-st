from django.contrib import admin
from django.contrib.admin import display
from django.utils.safestring import mark_safe
from django.db.models import Count

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
    """Фильтр по времени готовки с умными подписями."""
    title = 'время готовки'
    parameter_name = 'cooking_time_range'

    def lookups(self, request, model_admin):
        recipes_count = Recipe.objects.count()
        if recipes_count == 0:
            return []

        quick_count = Recipe.objects.filter(cooking_time__lte=30).count()
        medium_count = Recipe.objects.filter(
            cooking_time__gt=30, cooking_time__lte=60).count()
        long_count = Recipe.objects.filter(cooking_time__gt=60).count()

        return [
            ('quick', f'быстрее 30 мин ({quick_count})'),
            ('medium', f'30-60 мин ({medium_count})'),
            ('long', f'больше 60 мин ({long_count})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'quick':
            return queryset.filter(cooking_time__lte=30)
        if self.value() == 'medium':
            return queryset.filter(cooking_time__gt=30, cooking_time__lte=60)
        if self.value() == 'long':
            return queryset.filter(cooking_time__gt=60)


class HasRecipesFilter(admin.SimpleListFilter):
    """Фильтр ингредиентов по наличию в рецептах."""
    title = 'есть в рецептах'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Да'),
            ('no', 'Нет'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipe_ingredients__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipe_ingredients__isnull=True)


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
        return recipe.favorites.count()

    @mark_safe
    @display(description='Ингредиенты')
    def get_ingredients_display(self, recipe):
        """Возвращает HTML-разметку списка ингредиентов."""
        ingredients = recipe.recipe_ingredients.select_related(
            'ingredient')[:3]
        if not ingredients:
            return '<span style="color: #999;">Нет ингредиентов</span>'

        ingredients_list = []
        for recipe_ingredient in ingredients:
            ingredients_list.append(
                f'{recipe_ingredient.ingredient.name} '
                f'({recipe_ingredient.amount}'
                f'{recipe_ingredient.ingredient.measurement_unit})'
            )

        result = '<br>'.join(ingredients_list)
        if recipe.recipe_ingredients.count() > 3:
            remaining = recipe.recipe_ingredients.count() - 3
            result += f'<br><i>...и еще {remaining}</i>'

        return result

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
            'favorites'
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
        return ingredient.recipes_count if hasattr(
            ingredient, 'recipes_count'
        ) else ingredient.recipe_ingredients.count()

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
