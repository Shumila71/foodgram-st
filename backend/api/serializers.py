from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from rest_framework import serializers
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart
)
from users.models import Follow

User = get_user_model()


class FoodgramUserSerializer(UserSerializer):
    """Сериализатор для пользователя."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed'
        )
        read_only_fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'avatar', 'is_subscribed')

    def get_is_subscribed(self, user):
        """Проверяет, подписан ли текущий пользователь на просматриваемого."""
        request = self.context.get('request')
        return (
            request and not request.
            user.is_anonymous and Follow.objects.filter(
                user=request.user, author=user).exists()
        )

    def validate_avatar(self, value):
        """Валидация аватара."""
        if not value:
            return value
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError(
                'Размер файла не должен превышать 2MB.'
            )

        allowed_extensions = ['jpg', 'jpeg', 'png']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                'Поддерживаются только форматы JPG и PNG.'
            )

        return value

    def update(self, instance, validated_data):
        """Обновление пользователя."""
        try:
            if 'avatar' in validated_data:
                if validated_data['avatar'] is None and instance.avatar:
                    instance.avatar.delete()
                    instance.avatar = None
            return super().update(instance, validated_data)
        except Exception as e:
            raise serializers.ValidationError(
                f'Ошибка при обновлении профиля: {str(e)}'
            )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = FoodgramUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, recipe):
        user = self.context.get('request').user
        return (
            not user.is_anonymous and Favorite.objects.filter(
                user=user, recipe=recipe).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        user = self.context.get('request').user
        return (
            not user.is_anonymous and ShoppingCart.objects.filter(
                user=user, recipe=recipe).exists()
        )


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(
        many=True,
        source='recipe_ingredients',
        required=True
    )
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def validate(self, data):
        if self.context['request'].method in ['PATCH', 'PUT']:
            if 'recipe_ingredients' not in data:
                raise serializers.ValidationError(
                    {'ingredients': 'Обязательное поле.'}
                )
        return data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один ингредиент'
            )

        ingredients_set = set()
        for item in value:
            ingredient_id = item['id'].id
            if ingredient_id in ingredients_set:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться'
                )
            ingredients_set.add(ingredient_id)
        return value

    def validate_image(self, value):
        if value:
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Размер изображения не должен превышать 2MB'
                )

            allowed_extensions = ['jpg', 'jpeg', 'png']
            ext = value.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    'Поддерживаются только форматы JPG и PNG'
                )
        return value

    def _create_ingredients(self, recipe, ingredients):
        """Создание ингредиентов для рецепта."""
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context=self.context
        ).data

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('recipe_ingredients')
        validated_data['author'] = self.context['request'].user
        recipe = super().create(validated_data)
        self._create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'recipe_ingredients' in validated_data:
            instance.recipe_ingredients.all().delete()
            ingredients = validated_data.pop('recipe_ingredients')
            self._create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)


class FollowListSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
            'recipes', 'recipes_count'
        )
        read_only_fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
            'recipes', 'recipes_count'
        )

    def get_recipes(self, user):
        request = self.context.get('request')
        limit = int(request.GET.get('recipes_limit', 10**10))
        recipes = user.recipes.all()[:limit]
        return RecipeShortSerializer(recipes, many=True).data

    def get_is_subscribed(self, user):
        request = self.context.get('request')
        return (
            request and not request.user.is_anonymous and Follow.
            objects.filter(
                user=request.user, author=user).exists()
        )


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецепта в подписках."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')
