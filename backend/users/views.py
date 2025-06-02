from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from djoser.views import UserViewSet

from api.serializers import (
    CustomUserSerializer,
    FollowSerializer,
    FollowListSerializer
)
from .models import Follow
from api.pagination import CustomPageNumberPagination

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserSerializer
    queryset = User.objects.all()
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return super().get_serializer_class()
        return CustomUserSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {'error': 'Необходимо указать текущий и новый пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post', 'put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request):
        try:
            user = request.user
            if request.method in ['POST', 'PUT']:
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

        except serializers.ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
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
    def subscribe(self, request, **kwargs):
        try:
            author = get_object_or_404(User, id=kwargs.get('id'))

            if request.method == 'POST':
                if Follow.objects.filter(
                        user=request.user, author=author).exists():
                    return Response(
                        {'errors': 'Вы уже подписаны на этого пользователя'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if request.user == author:
                    return Response(
                        {'errors': 'Нельзя подписаться на самого себя'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                follow = Follow.objects.create(
                    user=request.user, author=author)
                serializer = FollowSerializer(
                    follow,
                    context={'request': request}
                )
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED)

            follow = Follow.objects.filter(
                user=request.user,
                author=author
            ).first()

            if not follow:
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except User.DoesNotExist:
            return Response(
                {'errors': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        try:
            users = User.objects.filter(following__user=request.user)
            if not users.exists():
                return Response(
                    {'results': [], 'count': 0},
                    status=status.HTTP_200_OK
                )

            pages = self.paginate_queryset(users)
            if pages is None:
                serializer = FollowListSerializer(
                    users,
                    many=True,
                    context={'request': request}
                )
                return Response(serializer.data)

            serializer = FollowListSerializer(
                pages,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
