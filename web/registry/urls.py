from django.urls import path, include
from .views import RunViewSet
from .views import RepoViewSet
from .views import ComponentViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r"components", ComponentViewSet, basename="component")
router.register(r"runs", RunViewSet)
router.register(r"repos", RepoViewSet, basename="repo")

router.get_api_root_view().cls.__name__ = "Root"
router.get_api_root_view().cls.__doc__ = "AgentOS Registry API views"

# import pprint; pprint.pprint(router.urls)

print("router.urls is:")
print(router.urls)

urlpatterns = [
    path("v1/", include(router.urls)),
]
