from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ComponentViewSet

router = DefaultRouter()
router.register(r"components", ComponentViewSet, basename="component")

router.get_api_root_view().cls.__name__ = "Root"
router.get_api_root_view().cls.__doc__ = "AgentOS Registry API views"

# import pprint; pprint.pprint(router.urls)

urlpatterns = [
    path("v1/", include(router.urls)),
]
