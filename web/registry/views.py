import yaml
import json
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from .models import Component
from .models import ComponentDependency
from .models import Repo
from .models import Run
from .serializers import ComponentSerializer


class ComponentViewSet(viewsets.ModelViewSet):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["POST"], url_name="ingest-spec")
    @transaction.atomic
    def ingest_spec(self, request, *args, **kwargs):
        SPEC_NAME = "components.yaml"
        if SPEC_NAME not in request.data:
            raise ValidationError(f"No {SPEC_NAME} included in ingest request")
        component_spec = request.data[SPEC_NAME]
        spec_dict = yaml.safe_load(component_spec)
        repo_dict = spec_dict.get("repos", {})
        component_dict = spec_dict.get("components", {})
        Repo.create_from_dict(repo_dict)
        components = Component.create_from_dict(component_dict)
        ComponentDependency.create_from_dict(component_dict)
        serialized = ComponentSerializer(components, many=True)
        return Response(serialized.data)


def index(request):
    return HttpResponse(
        "Hello, world. You're at the registry index."
        f"There are {Component.objects.count()} Components with "
        f"{ComponentDependency.objects.count()} dependencies."
    )


def component_detail(request, component_id):
    component = get_object_or_404(Component, pk=component_id)
    context = {
        "runs": Run.objects.filter(components=component).order_by("-id"),
        "component": component,
    }
    return render(request, "registry/component_detail.html", context)


def run_detail(request, run_id):
    run = get_object_or_404(Run, pk=run_id)
    context = {"run": run}
    return render(request, "registry/run_detail.html", context)


def api_components(request):
    all_components = {}
    for component in Component.objects.all():
        releases = []
        component_data = {
            "type": component.component_type_text.lower(),
            "description": component.description,
            "releases": releases,
        }
        for release in component.releases.all():
            release_data = {
                "name": release.name,
                "hash": release.git_hash,
                "github_url": release.github_url,
                "file_path": release.file_path,
                "class_name": release.class_name,
                "requirements_path": release.requirements_path,
            }
            releases.append(release_data)
        all_components[component.name] = component_data
    return HttpResponse(yaml.dump(all_components))


@csrf_exempt
def api_runs(request):
    data = json.loads(request.body)
    benchmark_data = data["benchmark_data"]
    agent_data = data["agent_data"]
    run = Run(benchmark_data=benchmark_data, agent_data=agent_data)
    run.save()
    for component in agent_data:
        component = Component.objects.get(name=component["package_name"])
        run.components.add(component)
    return JsonResponse({"run_id": run.id})


@csrf_exempt
def api_tarball(request, run_id):
    run = get_object_or_404(Run, pk=run_id)
    run.tarball = request.FILES["file"]
    run.save()
    return HttpResponse("Ok!")


def run_tarball(request, run_id):
    run = get_object_or_404(Run, pk=run_id)
    response = HttpResponse(
        run.tarball.read(), content_type="application/tar.gz"
    )
    response[
        "Content-Disposition"
    ] = f"attachment; filename=run{run_id}.tar.gz"
    return response
