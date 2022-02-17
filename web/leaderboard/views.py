from django.urls import reverse
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponseBadRequest
from registry.models import ComponentDependency
from registry.models import Component
from registry.models import Repo
from registry.models import Run


def index(request):
    environments = Component.objects.filter(
        runs_as_environment__isnull=False
    ).distinct()
    context = {
        "environments": environments,
        "is_debug": settings.DEBUG,
    }
    return render(request, "leaderboard/index.html", context)


def empty_database(request):
    if not settings.DEBUG:
        raise HttpResponseBadRequest("Not allowed.")
    ComponentDependency.objects.all().delete()
    Component.objects.all().delete()
    Repo.objects.all().delete()
    Run.objects.all().delete()
    return HttpResponseRedirect(reverse("index"))
