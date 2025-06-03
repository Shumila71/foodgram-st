from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FoodgramUserViewSet,
    IngredientViewSet,
    RecipeViewSet,
)

app_name = 'api'

router = DefaultRouter()
router.register('users', FoodgramUserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
