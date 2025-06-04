from datetime import datetime
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from djoser.views import UserViewSet

from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter
from .pagination import FoodgramPageNumberPagination
from .serializers import (
    FoodgramUserSerializer,
    UserWithRecipesSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeWriteSerializer,
    RecipeShortSerializer
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart
)
from users.models import Follow

User = get_user_model()


class FoodgramUserViewSet(UserViewSet):
    """ViewSet для работы с пользователями."""
    serializer_class = FoodgramUserSerializer
    queryset = User.objects.all()
    pagination_class = FoodgramPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            if not request.data.get('avatar'):
                return Response(
                    {'error': 'Файл аватара не предоставлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(
                user,
                data={'avatar': request.data.get('avatar')},
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'avatar': serializer.data['avatar']},
                status=status.HTTP_200_OK
            )

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, **kwargs):
        author_id = kwargs.get('id')

        if request.method == 'DELETE':
            follow = get_object_or_404(
                Follow, user=request.user, author_id=author_id
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        author = get_object_or_404(User, id=author_id)
        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow, created = Follow.objects.get_or_create(
            user=request.user, author=author
        )
        if not created:
            return Response(
                {'errors': f'Вы уже подписаны на пользователя'
                 f'{author.username}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserWithRecipesSerializer(
            author,
            context={'request': request}
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        users = User.objects.filter(author_subscriptions__user=request.user)
        pages = self.paginate_queryset(users)
        serializer = UserWithRecipesSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeSerializer

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self._add_to(Favorite, request.user, pk)
        return self._remove_from(Favorite, request.user, pk)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self._add_to(ShoppingCart, request.user, pk)
        return self._remove_from(ShoppingCart, request.user, pk)

    def _add_to(self, model, user, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        obj, created = model.objects.get_or_create(user=user, recipe=recipe)
        if not created:
            return Response(
                {'error': f'Рецепт "{recipe.name}" '
                 f'уже добавлен в {model._meta.verbose_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RecipeShortSerializer(
            recipe, context={'request': self.request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_from(self, model, user, pk):
        obj = get_object_or_404(model, user=user, recipe_id=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user

        ingredients = RecipeIngredient.objects.filter(
            recipe__shoppingcart__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount')).order_by('ingredient__name')

        shopping_cart_recipes = Recipe.objects.filter(
            shoppingcart__user=user
        ).select_related('author')

        current_date = datetime.now().strftime('%d.%m.%Y')

        shopping_list_content = '\n'.join([
            f'Список покупок от {current_date}',
            '',
            'ПРОДУКТЫ:',
            *[f'{i}. {ingredient["ingredient__name"].capitalize()} - '
              f'{ingredient["amount"]}'
              f' {ingredient["ingredient__measurement_unit"]}'
              for i, ingredient in enumerate(ingredients, start=1)],
            '',
            'РЕЦЕПТЫ:',
            *[f'• "{recipe.name}" (автор: '
              f' {recipe.author.get_full_name() or recipe.author.username})'
              for recipe in shopping_cart_recipes],
        ])

        response = FileResponse(
            shopping_list_content,
            as_attachment=True,
            filename='shopping_list.txt',
            content_type='text/plain'
        )
        return response

    @action(
        detail=True,
        methods=("get",),
        url_path="get-link",
        url_name="get-link",
    )
    def get_link(self, request, pk=None):
        """
        Получает короткую ссылку на рецепт
        """
        if not Recipe.objects.filter(pk=pk).exists():
            raise Http404
        short_url = reverse('recipes:short_link', kwargs={'recipe_id': pk})
        short_link = request.build_absolute_uri(short_url)
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)
