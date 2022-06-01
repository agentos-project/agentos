from collections import defaultdict

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from registry.models import Component


def index(request):
    run_obj_by_id, env_obj_by_id, _, terminals, _, _ = Run.agent_run_dags()
    env_dict = defaultdict(list)
    for env_id, run_list in terminals.items():
        runs = sorted(
            run_list,
            key=(lambda i: run_obj_by_id[i].data["metrics"]["mean_reward"]),
            reverse=True,
        )
        env_obj = env_obj_by_id[env_id]
        env_dict[env_obj] = [run_obj_by_id[run_id] for run_id in runs]
    context = {"env_dict": dict(env_dict), "is_debug": settings.DEBUG}
    return render(request, "leaderboard/index.html", context)


def run_list(request):
    agent_runs = Run.objects.filter(
        data__tags__contains={"pcs.is_agent_run": "True"}
    )
    component_runs = Run.objects.filter(
        data__tags__contains={"pcs.is_component_run": "True"}
    )
    context = {
        "agent_runs": agent_runs,
        "component_runs": component_runs,
        "is_debug": settings.DEBUG,
    }
    return render(request, "leaderboard/runs.html", context)


def run_detail(request, identifier):
    run = Run.objects.get(identifier=identifier)
    run_dag = Run.agent_run_dag(identifier, learn_only=True)
    context = {"run": run, "run_dag": run_dag, "is_debug": settings.DEBUG}
    return render(request, "leaderboard/run_detail.html", context)


def empty_database(request):
    if not settings.DEBUG:
        raise HttpResponseBadRequest("Not allowed.")
    ComponentDependency.objects.all().delete()
    Component.objects.all().delete()
    Repo.objects.all().delete()
    Run.objects.all().delete()
    return HttpResponseRedirect(reverse("index"))
