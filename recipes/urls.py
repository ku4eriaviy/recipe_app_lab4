from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search_recipes, name='search_recipes'),
    path('delete/<int:recipe_id>/', views.delete_recipe, name='delete_recipe'),
]