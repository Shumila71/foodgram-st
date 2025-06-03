from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.db.models import Count

from .models import Follow, User


class HasRecipesListFilter(admin.SimpleListFilter):
    """Фильтр по наличию рецептов."""
    title = 'есть рецепты'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Да'),
            ('no', 'Нет'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)


class HasSubscriptionsListFilter(admin.SimpleListFilter):
    """Фильтр по наличию подписок."""
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Да'),
            ('no', 'Нет'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(subscriptions__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(subscriptions__isnull=True)


class HasFollowersListFilter(admin.SimpleListFilter):
    """Фильтр по наличию подписчиков."""
    title = 'есть подписчики'
    parameter_name = 'has_followers'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Да'),
            ('no', 'Нет'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(subscribers__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(subscribers__isnull=True)


@admin.register(User)
class FoodgramUserAdmin(UserAdmin):
    """Административное представление пользователей."""

    list_display = (
        'id',
        'username',
        'get_full_name',
        'email',
        'get_avatar_display',
        'get_recipes_count',
        'get_subscriptions_count',
        'get_followers_count',
    )
    list_filter = (
        HasRecipesListFilter,
        HasSubscriptionsListFilter,
        HasFollowersListFilter,
        'is_active',
        'is_staff',
        'date_joined',
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('get_avatar_display',)

    def get_queryset(self, request):
        """Оптимизированный queryset с подсчетом связанных объектов."""
        return super().get_queryset(request).annotate(
            recipes_count=Count('recipes', distinct=True),
            subscriptions_count=Count('subscriptions', distinct=True),
            followers_count=Count('subscribers', distinct=True)
        )

    def get_full_name(self, obj):
        """Возвращает полное имя пользователя."""
        return f"{obj.first_name} {obj.last_name}".strip()
    get_full_name.short_description = 'ФИО'

    @mark_safe
    def get_avatar_display(self, obj):
        """Возвращает HTML-разметку для отображения аватара."""
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="50" height="50" '
            'style="border-radius: 50%; object-fit: cover;" />'
        return '<span style="color: #999;">Нет аватара</span>'
    get_avatar_display.short_description = 'Аватар'

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes_count if hasattr(
            obj, 'recipes_count') else obj.recipes.count()
    get_recipes_count.short_description = 'Рецептов'

    def get_subscriptions_count(self, obj):
        """Возвращает количество подписок пользователя."""
        return obj.subscriptions_count if hasattr(
            obj, 'subscriptions_count') else obj.subscriptions.count()
    get_subscriptions_count.short_description = 'Подписок'

    def get_followers_count(self, obj):
        """Возвращает количество подписчиков пользователя."""
        return obj.followers_count if hasattr(
            obj, 'followers_count') else obj.subscribers.count()
    get_followers_count.short_description = 'Подписчиков'


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Административное представление подписок."""

    list_display = ('id', 'user', 'author',
                    'get_user_email', 'get_author_email')
    list_filter = ('user__is_active', 'author__is_active')
    search_fields = (
        'user__username',
        'user__email',
        'author__username',
        'author__email',
        'user__first_name',
        'user__last_name',
        'author__first_name',
        'author__last_name'
    )
    list_select_related = ('user', 'author')

    def get_user_email(self, obj):
        """Возвращает email подписчика."""
        return obj.user.email
    get_user_email.short_description = 'Email подписчика'

    def get_author_email(self, obj):
        """Возвращает email автора."""
        return obj.author.email
    get_author_email.short_description = 'Email автора'
