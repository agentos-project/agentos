from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentRunViewSet,
    ComponentViewSet,
    RepoViewSet,
    RunCommandViewSet,
    RunViewSet,
)

router = DefaultRouter()
router.register(r"agentruns", AgentRunViewSet, basename="agentrun")
router.register(r"runs", RunViewSet)
router.register(r"runcommands", RunCommandViewSet, basename="runcommand")
router.register(r"components", ComponentViewSet, basename="component")
router.register(r"repos", RepoViewSet, basename="repo")

router.get_api_root_view().cls.__name__ = "Root"
router.get_api_root_view().cls.__doc__ = "AgentOS Registry API views"

# import pprint; pprint.pprint(router.urls)

urlpatterns = [
    path("v1/", include(router.urls)),
]
