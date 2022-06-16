from collections import defaultdict

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from registry.models import Component


def index(request):
    agent_run_dags = Component.agent_run_dags()
    run_obj_by_id, env_obj_by_id, _, terminals, _, _ = agent_run_dags
    env_dict = defaultdict(list)
    for env_id, run_list in terminals.items():
        runs = sorted(
            run_list,
            key=lambda i: run_obj_by_id[i].mean_reward,
            reverse=True,
        )
        env_obj = env_obj_by_id[env_id]
        env_dict[env_obj] = [run_obj_by_id[run_id] for run_id in runs]
    context = {"env_dict": dict(env_dict), "is_debug": settings.DEBUG}
    return render(request, "leaderboard/index.html", context)


def run_list(request):
    print("HERE0")
    agent_runs = Component.objects.filter(
        body__data__tags__contains={"pcs.is_agent_run": "True"}
    )
    print(agent_runs)
    print("HERE1")
    component_runs = Component.objects.filter(
        body__data__tags__contains={"pcs.is_component_run": "True"}
    )
    print("HERE2")
    context = {
        "agent_runs": agent_runs,
        "component_runs": component_runs,
        "is_debug": settings.DEBUG,
    }
    print("CONTEXT")
    print(context)
    print("CONTEXT_DONE")
    return render(request, "leaderboard/runs.html", context)


def run_detail(request, identifier):
    run = Component.objects.get(identifier=identifier)
    run_dag = Component.agent_run_dag(identifier, learn_only=True)
    context = {"run": run, "run_dag": run_dag, "is_debug": settings.DEBUG}
    return render(request, "leaderboard/run_detail.html", context)


def empty_database(request):
    if not settings.DEBUG:
        return HttpResponseBadRequest("Not allowed.")
    # ComponentDependency.objects.all().delete()
    Component.objects.all().delete()
    # Repo.objects.all().delete()
    # Run.objects.all().delete()
    return HttpResponseRedirect(reverse("index"))
