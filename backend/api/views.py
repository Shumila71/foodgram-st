from django.db.models import Sum
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter, IngredientFilter
from .pagination import CustomPageNumberPagination
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    RecipeShortSerializer,
    RecipeLinkSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientFilter
    search_fields = ('^name',)

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset.order_by('name')

    def get_object(self):
        """
        Returns the object the view is displaying.
        Raises Http404 if object does not exist.
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update', 'update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        try:
            queryset = Recipe.objects.select_related(
                'author'
            ).prefetch_related(
                'ingredients',
                'recipe_ingredients',
                'favorites',
                'shopping_cart'
            )

            author = self.request.query_params.get('author')
            if author and str(author).isdigit():
                queryset = queryset.filter(author_id=author)

            is_favorited = self.request.query_params.get('is_favorited')
            if is_favorited and self.request.user.is_authenticated:
                if is_favorited in ['1', 'true']:
                    queryset = queryset.filter(
                        favorites__user=self.request.user)
                elif is_favorited in ['0', 'false']:
                    queryset = queryset.exclude(
                        favorites__user=self.request.user)

            is_in_shopping_cart = self.request.query_params.get(
                'is_in_shopping_cart')
            if is_in_shopping_cart and self.request.user.is_authenticated:
                if is_in_shopping_cart in ['1', 'true']:
                    queryset = queryset.filter(
                        shopping_cart__user=self.request.user
                    )
                elif is_in_shopping_cart in ['0', 'false']:
                    queryset = queryset.exclude(
                        shopping_cart__user=self.request.user
                    )

            return queryset.order_by('-pub_date')
        except Exception as e:
            raise ValidationError(str(e))

    def perform_create(self, serializer):
        try:
            serializer.save(author=self.request.user)
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(str(e))

    def create(self, request, *args, **kwargs):
        try:
            print(f"Creating recipe with data: {request.data}")

            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                print(f"Validation errors: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except ValidationError as e:
            print(f"Validation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.author != request.user:
                return Response(
                    {
                        'error': (
                            'У вас нет прав на редактирование '
                            'этого рецепта'
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=kwargs.get('partial', False)
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Http404:
            return Response(
                {'error': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(str(e))

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        try:
            recipe = get_object_or_404(Recipe, id=pk)

            if request.method == 'POST':
                if ShoppingCart.objects.filter(
                        user=request.user, recipe=recipe).exists():
                    return Response(
                        {'errors': 'Рецепт уже в списке покупок'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                shopping_cart = ShoppingCart.objects.create(
                    user=request.user,
                    recipe=recipe
                )
                serializer = RecipeShortSerializer(recipe)
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED)

            shopping_cart = ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).first()

            if not shopping_cart:
                return Response(
                    {'errors': 'Рецепт не находится в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Recipe.DoesNotExist:
            return Response(
                {'errors': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        try:
            user = request.user
            shopping_cart = ShoppingCart.objects.filter(user=user)

            if not shopping_cart.exists():
                return Response(
                    {'error': 'Список покупок пуст'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ingredients = RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=user
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit'
            ).annotate(amount=Sum('amount'))

            shopping_list = []
            for item in ingredients:
                shopping_list.append(
                    f"{item['ingredient__name']} "
                    f"({item['ingredient__measurement_unit']}) - "
                    f"{item['amount']}"
                )

            content = 'Список покупок:\n\n' + '\n'.join(shopping_list)
            filename = f'shopping_list_{user.username}.txt'

            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = (
                f'attachment; filename={filename}'
            )
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        try:
            recipe = get_object_or_404(Recipe, id=pk)

            if request.method == 'POST':
                if Favorite.objects.filter(
                        user=request.user, recipe=recipe).exists():
                    return Response(
                        {'errors': 'Рецепт уже в избранном'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                favorite = Favorite.objects.create(
                    user=request.user,
                    recipe=recipe
                )
                serializer = RecipeShortSerializer(
                    recipe)
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED)

            favorite = Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).first()

            if not favorite:
                return Response(
                    {'errors': 'Рецепт не находится в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Recipe.DoesNotExist:
            return Response(
                {'errors': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    def perform_destroy(self, instance):
        """Delete a recipe instance."""
        if instance.author != self.request.user:
            raise PermissionDenied(
                'У вас нет прав на удаление этого рецепта'
            )
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """Handle DELETE request to delete a recipe."""
        try:
            try:
                instance = self.get_object()
            except Http404:
                return Response(
                    {'errors': 'Рецепт не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if instance.author != request.user:
                return Response(
                    {'errors': 'У вас нет прав на удаление этого рецепта'},
                    status=status.HTTP_403_FORBIDDEN
                )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionDenied as e:
            return Response(
                {'errors': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'errors': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Http404:
            return Response(
                {'error': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        try:
            recipe = get_object_or_404(Recipe, id=pk)
            serializer = RecipeLinkSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {'errors': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
