from django.urls import path

from .views import recipe_short_link

app_name = 'recipes'

urlpatterns = [
    path('s/<int:recipe_id>/', recipe_short_link, name='short_link'),
]
