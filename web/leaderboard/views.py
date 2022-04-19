from collections import defaultdict

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from registry.models import Component, ComponentDependency, Repo, Run


def index(request):
    run_objs = Run.objects.filter(environment__isnull=False)
    run_obj_by_id = {}
    env_obj_by_id = {}
    for run in run_objs:
        run_obj_by_id[run.identifier] = run
        env_obj_by_id[run.environment.identifier] = run.environment

    run_dicts = Run.objects.filter(environment__isnull=False).values()
    run_id_to_run = {}
    run_to_env_id = {}

    # {env_id: {agent_id: [runs_without_input_parents]}}
    root_runs = defaultdict(lambda: defaultdict(list))
    run_graph = {}  # {parent_id: child_id}
    # Ignore any runs with parents
    for run_d in run_dicts:
        # Store our roots, which we'll use to for traversal later
        agent_id = run_d["agent_id"]
        env_id = run_d["environment_id"]
        run_id = run_d["identifier"]
        run_id_to_run[run_id] = run_d
        tags = run_d["data"]["tags"]
        run_to_env_id[run_id] = env_id
        if "model_input_run_id" not in tags:
            root_runs[env_id][agent_id].append(run_id)
            print("run_root: ", run_id)
        # store graph edges from parent to child (opposite of how they are)
        else:
            parent_id = tags["model_input_run_id"]
            run_graph[parent_id] = run_id
            print(f"run_graph[{parent_id}] = {run_id}")
            print("non_root: ", run_id)

    # find the terminal node for every root_run (might be itself, i.e. no edge)
    terminals = defaultdict(list)
    for env_id in root_runs.values():
        for root_list in env_id.values():
            for root in root_list:
                print(f"finding terminal node for {root}")
                terminal = root
                while terminal in run_graph:
                    terminal = run_graph[terminal]
                    print(f"terminal node changed to {terminal}")
                print(f"Done. looking up {terminal} in {run_to_env_id}")
                env_id = run_to_env_id[terminal]
                terminals[env_id].append(terminal)

    env_dict = defaultdict(list)
    for env_id, run_list in terminals.items():
        print(f"handling terminals for env_id {env_id}: {run_list}")
        runs = sorted(
            run_list,
            key=(
                lambda i: run_id_to_run[i]["data"]["metrics"]["mean_reward"]
            ),
            reverse=True
        )
        env_obj = env_obj_by_id[env_id]
        env_dict[env_obj] = [run_obj_by_id[run_id] for run_id in runs]
    print("env_dict is:", dict(env_dict))
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
