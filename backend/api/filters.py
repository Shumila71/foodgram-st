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

    def filter_is_favorited(self, recipes, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return recipes.filter(favorite__user=user)
        elif not value and not user.is_anonymous:
            return recipes.exclude(favorite__user=user)
        return recipes

    def filter_is_in_shopping_cart(self, recipes, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return recipes.filter(shoppingcart__user=user)
        elif not value and not user.is_anonymous:
            return recipes.exclude(shoppingcart__user=user)
        return recipes

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart')


class IngredientFilter(FilterSet):
    """Фильтры для ингредиентов."""

    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
