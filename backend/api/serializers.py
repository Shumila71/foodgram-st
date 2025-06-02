from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
import base64
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import status
import uuid

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart
)
from users.models import Follow

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            if ext not in ['jpeg', 'jpg', 'png']:
                raise serializers.ValidationError(
                    'Неподдерживаемый формат изображения'
                )

            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )

        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True, 'write_only': True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует.'
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class CustomUserSerializer(UserSerializer):
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

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на просматриваемого."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=request.user, author=obj).exists()

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

    def to_representation(self, instance):
        """Преобразование объекта в словарь."""
        if instance is None or instance.is_anonymous:
            return {
                'detail': 'Не авторизован',
                'status_code': status.HTTP_401_UNAUTHORIZED
            }
        data = super().to_representation(instance)
        if instance.avatar:
            data['avatar'] = self.context['request'].build_absolute_uri(
                instance.avatar.url
            )
        return data


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
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

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1, max_value=32767)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше 0!'
            )
        if value > 32767:
            raise serializers.ValidationError(
                'Слишком большое количество ингредиента!'
            )
        return value

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value.id).exists():
            raise serializers.ValidationError(
                f'Ингредиент с id={value.id} не существует!'
            )
        return value

    def validate(self, data):
        if 'id' not in data:
            raise serializers.ValidationError(
                'Поле id обязательно!'
            )
        if 'amount' not in data:
            raise serializers.ValidationError(
                'Поле amount обязательно!'
            )
        return data


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(
        many=True,
        source='recipe_ingredients',
        required=True
    )
    image = Base64ImageField()
    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart'
        )

    def validate(self, data):
        if self.context['request'].method in ['PATCH', 'PUT']:
            if 'recipe_ingredients' not in data:
                raise serializers.ValidationError(
                    {'ingredients': 'Обязательное поле.'}
                )
        return data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj).exists()

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError('Название рецепта обязательно')
        if len(value) > 200:
            raise serializers.ValidationError(
                'Название рецепта не должно превышать 200 символов'
            )
        return value

    def validate_cooking_time(self, value):
        if value is not None and (not isinstance(value, int) or value < 1):
            raise serializers.ValidationError(
                'Время приготовления должно быть целым числом больше 0'
            )
        return value

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

            amount = item.get('amount')
            if amount is not None and (
                    not isinstance(amount, int) or amount < 1):
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть целым числом больше 0'
                )
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ingredients'] = RecipeIngredientSerializer(
            instance.recipe_ingredients.all(),
            many=True
        ).data
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ingredients = validated_data.pop('recipe_ingredients')

            validated_data['author'] = self.context['request'].user

            recipe = Recipe.objects.create(**validated_data)

            recipe_ingredients = []
            for item in ingredients:
                ingredient = item['id']
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=item['amount']
                    )
                )
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

            recipe.refresh_from_db()
            return recipe
        except Exception as e:
            raise serializers.ValidationError(
                f'Ошибка при создании рецепта: {str(e)}')

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            if 'recipe_ingredients' in validated_data:
                instance.recipe_ingredients.all().delete()
                ingredients = validated_data.pop('recipe_ingredients')
                recipe_ingredients = [
                    RecipeIngredient(
                        recipe=instance,
                        ingredient=item['id'],
                        amount=item['amount']
                    )
                    for item in ingredients
                ]
                RecipeIngredient.objects.bulk_create(recipe_ingredients)

            return super().update(instance, validated_data)
        except Exception as e:
            raise serializers.ValidationError(
                f'Ошибка при обновлении рецепта: {str(e)}')


class FollowSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def validate(self, data):
        request = self.context.get('request')
        author = self.context.get('author')
        if request.user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )
        if Follow.objects.filter(user=request.user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя'
            )
        return data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=request.user,
            author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.author.recipes.all()
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        serializer = RecipeShortSerializer(
            recipes,
            many=True
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.author.avatar:
            return request.build_absolute_uri(obj.author.avatar.url)
        return None


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецепта в подписках."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowListSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=request.user,
            author=obj
        ).exists()


class RecipeLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ()

    def to_representation(self, instance):
        return {
            'short-link': f'http://localhost/recipes/{instance.id}'
        }
