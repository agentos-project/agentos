from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/components/", views.api_components, name="api_components"),
    path("api/runs/", views.api_runs, name="api_runs"),
    path(
        "api/runs/<int:run_id>/tarball",
        views.api_tarball,
        name="api_tarball",
    ),
    path(
        "components/<int:component_id>/",
        views.component_detail,
        name="component_detail",
    ),
    path("runs/<int:run_id>/", views.run_detail, name="run_detail"),
    path("runs/<int:run_id>/tarball", views.run_tarball, name="run_tarball"),
]
