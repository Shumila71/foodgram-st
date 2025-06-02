from django_filters import rest_framework as filters
from django_filters.rest_framework import (
    FilterSet,
    CharFilter,
)

from recipes.models import Ingredient, Recipe, User


class RecipeFilter(FilterSet):
    """Фильтры для рецептов."""

    author = filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        field_name='author'
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(favorites__user=user)
        elif value is False and not user.is_anonymous:
            return queryset.exclude(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(shopping_cart__user=user)
        elif value is False and not user.is_anonymous:
            return queryset.exclude(shopping_cart__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart')


class IngredientFilter(FilterSet):
    """Фильтры для ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
