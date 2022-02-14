# import yaml
from django.db import transaction

# from django.urls import reverse
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from .models import Repo, Component, RunCommand, Run
from .serializers import (
    RunSerializer,
    RepoSerializer,
    ComponentSerializer,
    RunCommandSerializer,
)


# TODO: This used to be a member of ComponentViewSet that also called a static
#       method of the Component model ingest_registry_dict(), but it should be
#       refactored to be its own stand-alone view, since ingest_registry view
#       is not specific to a model but potentially creates objects across all
#       model types.
# @action(detail=False, methods=["POST"], url_name="ingest-registry")
# @transaction.atomic
# def ingest_registry(self, request: Request, *args, **kwargs) -> Response:
#    REGISTRY_NAME = "components.yaml"
#    if REGISTRY_NAME not in request.data:
#        raise ValidationError(
#            f"No {REGISTRY_NAME} included in ingest request"
#        )
#    raw_reg = request.data[REGISTRY_NAME]
#    reg_dict = yaml.safe_load(raw_reg)
#    repo_reg_dict = reg_dict.get("repos", {})
#    component_reg_dict = reg_dict.get("components", {})
#    repos = Repo.create_from_dict(repo_reg_dict)
#    components = Component.create_from_dict(component_reg_dict)
#    ComponentDependency.create_from_dict(component_reg_dict)
#    serialized = ComponentSerializer(components, many=True)
#    return Response(serialized.data)


class RepoViewSet(viewsets.ModelViewSet):
    queryset = Repo.objects.all().order_by("-created")
    serializer_class = RepoSerializer
    permission_classes = [AllowAny]


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


def _get_from_list(name, component_list):
    components = [c for c in component_list if c.name == name]
    if len(components) > 1:
        raise ValidationError(f"Repeat components named {name}: {components}")
    if len(components) == 0:
        raise ValidationError(f"No component named {name}: {component_list}")
    return components[0]


class RunCommandViewSet(viewsets.ModelViewSet):
    queryset = RunCommand.objects.all().order_by("-created")
    serializer_class = RunCommandSerializer
    permission_classes = [AllowAny]


class RunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.all().order_by("-created")
    serializer_class = RunSerializer
    permission_classes = [AllowAny]

    # @transaction.atomic
    # def create(self, request):
    #     data = yaml.safe_load(request.data["run_data"])
    #     if Run.objects.filter(id=data["id"]).exists():
    #         host = request.headers.get("HOST", "")
    #         path = reverse("run-detail", kwargs={"pk": data["id"]})
    #         raise ValidationError(
    #             f"Run {data['id']} already exists!  View at {host}{path}"
    #         )
    #     # TODO - we should track provenance of all Components created
    #     repos, components = Component.ingest_spec_dict(
    #         data["component_spec"]
    #     )
    #     root = _get_from_list(data["root_component"], components)
    #     mlflow_params = data["mlflow_data"]["params"]
    #     agent = _get_from_list(mlflow_params["agent_name"], components)
    #     environment = _get_from_list(
    #         mlflow_params["environment_name"], components
    #     )
    #     run = Run.objects.create(
    #         id=data["id"],
    #         root=root,
    #         agent=agent,
    #         environment=environment,
    #         mlflow_metrics=data["mlflow_data"]["metrics"],
    #         mlflow_params=mlflow_params,
    #         mlflow_tags=data["mlflow_data"]["tags"],
    #         mlflow_info=data["mlflow_info"],
    #         entry_point=data["entry_point"],
    #         parameter_set=data["parameter_set"],
    #     )
    #     return Response(RunSerializer(run).data)

    @action(detail=True, methods=["POST"], url_name="upload-artifact")
    @transaction.atomic
    def upload_artifact(self, request: Request, pk=None) -> Response:
        run = self.get_object()
        run.artifact_tarball.save(
            f"run_{run.identifier}_artifacts.tar.gz", request.data["tarball"]
        )
        run.save()
        return Response(RunSerializer(run).data)

    @action(detail=True, methods=["GET"], url_name="download-artifact")
    def download_artifact(self, request: Request, pk=None) -> Response:
        run = self.get_object()
        if not run.artifact_tarball:
            raise ValidationError(
                f"No files associated with Run {run.identifier}"
            )
        response = HttpResponse(
            run.artifact_tarball.open(), content_type="application/gzip"
        )
        disposition = f"attachment; filename={run.artifact_tarball.name}"
        response["Content-Disposition"] = disposition
        return response


# TODO: this should be very similar to RunViewSet but filter to just Runs
#    from the Run table that have an agent and environemnt FK set.
class AgentRunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.filter(agent__isnull=False).order_by("-created")
    serializer_class = RunSerializer
    permission_classes = [AllowAny]


# TODO: this should be very similar to RunViewSet but filter to just Runs
#    from the Run table that have an RunCommand FK set.
class ComponentRunViewSet:
    pass
