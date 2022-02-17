from django.urls import path

from . import views


urlpatterns = [
    path("empty_database", views.empty_database, name="empty-database"),
    path("", views.index, name="index"),
]
