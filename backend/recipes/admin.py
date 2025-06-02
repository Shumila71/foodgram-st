from django.contrib import admin
from django.contrib.admin import display

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


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для ингредиентов рецепта."""

    model = RecipeIngredient
    min_num = 1
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Административное представление рецептов."""

    list_display = ('name', 'author', 'favorites_count')
    search_fields = ('name', 'author__username')
    list_filter = ('author', 'name')
    inlines = (RecipeIngredientInline,)

    @display(description='В избранном')
    def favorites_count(self, obj):
        return obj.favorites.count()

    def get_queryset(self, request):
        """Возвращает оптимизированный queryset для списка рецептов."""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'author'
        ).prefetch_related('recipe_ingredients__ingredient')
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Административное представление ингредиентов рецепта."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin, OptimizedQuerysetMixin):
    """Административное представление избранного."""

    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin, OptimizedQuerysetMixin):
    """Административное представление списка покупок."""

    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'recipe')


admin.site.empty_value_display = '-пусто-'
