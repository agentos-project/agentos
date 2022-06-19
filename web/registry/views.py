from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Component
from .serializers import ComponentSerializer


class ComponentViewSet(viewsets.ModelViewSet):
    serializer_class = ComponentSerializer
    permission_classes = [AllowAny]
    lookup_value_regex = "[^/]+"  # Default PK regex does not allow periods.

    def get_queryset(self):
        queryset = Component.objects.all().order_by("-created")
        # filter by url .../components?name=name&version=comp_version
        name = self.request.query_params.get("name")
        version = self.request.query_params.get("version")
        if name:
            queryset = queryset.filter(name=name)
        if version:
            queryset = queryset.filter(version=version)
        return queryset

    @transaction.atomic
    def create(self, request):
        component = Component.create_from_request_data(request.data)
        serialized = ComponentSerializer(component)
        return Response(serialized.data)

    @action(detail=True, methods=["POST"], url_name="upload-artifact")
    @transaction.atomic
    def upload_artifact(self, request: Request, pk=None) -> Response:
        component = self.get_object()
        file_name = "component{component.identifier}_artifacts.tar.gz"
        component.artifact_tarball.save(file_name, request.data["tarball"])
        component.save()
        return Response(ComponentSerializer(component).data)

    @action(detail=True, methods=["GET"], url_name="download-artifact")
    def download_artifact(self, request: Request, pk=None) -> Response:
        component = self.get_object()
        if not component.artifact_tarball:
            raise ValidationError(
                f"No files associated with Component {component.identifier}"
            )
        response = HttpResponse(
            component.artifact_tarball.open(), content_type="application/gzip"
        )
        disposition = f"attachment; filename={component.artifact_tarball.name}"
        response["Content-Disposition"] = disposition
        return response


def _get_from_list(name, component_list):
    components = [c for c in component_list if c.name == name]
    if len(components) > 1:
        raise ValidationError(f"Repeat components named {name}: {components}")
    if len(components) == 0:
        raise ValidationError(f"No component named {name}: {component_list}")
    return components[0]
