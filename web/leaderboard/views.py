from django.shortcuts import render

from registry.models import Component
from registry.models import Run


def index(request):
    components = list(Component.objects.all())
    context = {
        "runs": Run.objects.all().order_by("-id"),
        "environments": [c for c in components if c.is_environment],
        "agents": [c for c in components if c.is_agent],
        "policies": [c for c in components if c.is_policy],
        "datasets": [c for c in components if c.is_dataset],
        "trainers": [c for c in components if c.is_trainer],
    }
    return render(request, "leaderboard/index.html", context)


def runs(request):
    context = {
        "runs": Run.objects.all().order_by("-id"),
    }
    return render(request, "leaderboard/runs.html", context)


def components(request):
    components = list(Component.objects.all())
    context = {
        "environments": [c for c in components if c.is_environment],
        "agents": [c for c in components if c.is_agent],
        "policies": [c for c in components if c.is_policy],
        "datasets": [c for c in components if c.is_dataset],
        "trainers": [c for c in components if c.is_trainer],
    }
    return render(request, "leaderboard/components.html", context)
