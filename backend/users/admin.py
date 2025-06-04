from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.db.models import Count

from .models import Follow, User


class BaseListFilter(admin.SimpleListFilter):
    """Базовый класс для фильтров по наличию связанных объектов."""

    LOOKUPS = [
        ('yes', 'Да'),
        ('no', 'Нет'),
    ]

    filter_field = None

    def lookups(self, request, model_admin):
        return self.LOOKUPS

    def queryset(self, request, objects):
        if not self.filter_field:
            return objects

        if self.value() == 'yes':
            return objects.filter(
                **{f'{self.filter_field}__isnull': False}).distinct()
        if self.value() == 'no':
            return objects.filter(
                **{f'{self.filter_field}__isnull': True})


class HasRecipesListFilter(BaseListFilter):
    """Фильтр по наличию рецептов."""
    title = 'есть рецепты'
    parameter_name = 'has_recipes'
    filter_field = 'recipes'


class HasSubscriptionsListFilter(BaseListFilter):
    """Фильтр по наличию подписок."""
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'
    filter_field = 'subscriptions'


class HasFollowersListFilter(BaseListFilter):
    """Фильтр по наличию подписчиков."""
    title = 'есть подписчики'
    parameter_name = 'has_followers'
    filter_field = 'author_subscriptions'


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

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username',
                       'first_name', 'last_name',
                       'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        """Оптимизированный queryset с подсчетом связанных объектов."""
        return super().get_queryset(request).annotate(
            recipes_count=Count('recipes', distinct=True),
            subscriptions_count=Count('subscriptions', distinct=True),
            followers_count=Count('author_subscriptions', distinct=True)
        )

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        """Возвращает полное имя пользователя."""
        return f"{obj.first_name} {obj.last_name}".strip()

    @admin.display(description='Аватар')
    @mark_safe
    def get_avatar_display(self, obj):
        """Возвращает HTML-разметку для отображения аватара."""
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="50"'
            'height="50" style="border-radius: 50%; object-fit: cover;" />'
        return '<span style="color: #999;">Нет аватара</span>'
    get_avatar_display.short_description = 'Аватар'

    @admin.display(description='Рецептов')
    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes_count

    @admin.display(description='Подписок')
    def get_subscriptions_count(self, obj):
        """Возвращает количество подписок пользователя."""
        return obj.subscriptions_count

    @admin.display(description='Подписчиков')
    def get_followers_count(self, obj):
        """Возвращает количество подписчиков пользователя."""
        return obj.followers_count


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

    @admin.display(description='Email подписчика')
    def get_user_email(self, obj):
        """Возвращает email подписчика."""
        return obj.user.email

    @admin.display(description='Email автора')
    def get_author_email(self, obj):
        """Возвращает email автора."""
        return obj.author.email
