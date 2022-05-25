import json
from collections import defaultdict
from typing import List, Tuple

from pcs.registry import WebRegistry
from pcs.component import Component as PCSComponent

from django.db import models
from django.http import QueryDict


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Component(TimeStampedModel):
    identifier = models.CharField(max_length=200, primary_key=True)
    body = models.JSONField(default=dict)

    @staticmethod
    def create_from_request_data(request_data: QueryDict):
        # get mutable version of request so that we can decode json fields. Per
        # https://docs.djangoproject.com/en/4.0/ref/request-response/#querydict-objects
        data = request_data.copy()
        identifier = data.pop(PCSComponent.IDENTIFIER_KEY)
        encoded_body = data[WebRegistry.SPEC_RESPONSE_BODY_KEY]
        flat_spec = json.decoder.JSONDecoder().decode(encoded_body)
        # TODO - When we have accounts, we need to check the the user
        #        has permission to create a new version of this Module
        #        (i.e. if the name already exists but not the version).
        component = Component.objects.create(
            identifier=identifier, body=flat_spec,
        )
        return component

    @staticmethod
    def agent_run_dags() -> Tuple:
        # TODO: FIX ME BY PORTING ME TO COMPONENTS_V2
        run_objs = Component.objects.filter(body__environment__isnull=False)
        run_obj_by_id = {}
        env_obj_by_id = {}
        run_to_env_id = {}
        node_to_root = {}

        # {env_id: {agent_id: [ids_of_runs_without_input_parents]}}
        root_run_ids = defaultdict(lambda: defaultdict(list))
        run_graph = {}  # {parent_id: child_id}
        for run in run_objs:
            run_obj_by_id[run.identifier] = run
            env_obj_by_id[run.body["environment"]] = run.environment
            agent_id = run.agent.identifier
            env_id = run.environment.identifier
            run_id = run.identifier
            tags = run.data["tags"]
            run_to_env_id[run_id] = env_id
            # Store our roots, which we'll use to for traversal later
            if "model_input_run_id" not in tags:
                root_run_ids[env_id][agent_id].append(run_id)
            # store graph edges from parent to child (opposite of how they are)
            else:
                parent_id = tags["model_input_run_id"]
                run_graph[parent_id] = run_id

        # find the terminal node for every root_run (might be itself)
        terminals = defaultdict(list)
        for env_id in root_run_ids.values():
            for root_id_list in env_id.values():
                for root_id in root_id_list:
                    terminal_id = root_id
                    node_to_root[root_id] = root_id
                    while terminal_id in run_graph:
                        terminal_id = run_graph[terminal_id]
                        assert terminal_id not in node_to_root
                        node_to_root[terminal_id] = root_id
                    env_id = run_to_env_id[terminal_id]
                    terminals[env_id].append(terminal_id)
        return (
            run_obj_by_id,
            env_obj_by_id,
            root_run_ids,
            terminals,
            node_to_root,
            run_graph,
        )

    @staticmethod
    def agent_run_dag(identifier) -> List:
        run_map, env_map, root_ids, term_ids, n2r, graph = Component.agent_run_dags()
        print(f"run_id_map.keys(): {run_map.keys()}")
        ident = n2r[identifier]
        res = [run_map[ident]]
        while ident in graph:
            ident = graph[ident]
            res.append(run_map[ident])
        return res
