from collections import defaultdict

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from registry.models import Component, ComponentDependency, Repo, Run


def index(request):
    runs = Run.objects.filter(environment__isnull=False)
    env_dict = defaultdict(list)
    for env, run in [(r.environment, r) for r in runs]:
        env_dict[env].append(run)
    print("env_dict: ", env_dict)
    context = {
        "env_dict": dict(env_dict),
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
