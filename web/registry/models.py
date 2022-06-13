import datetime
import json
from collections import defaultdict
from typing import List, Tuple

from django.db import models
from django.http import QueryDict

from pcs.component import Component as PCSComponent
from pcs.registry import WebRegistry


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Component(TimeStampedModel):
    SPEC_PREFIX = "spec:"

    identifier = models.CharField(max_length=200, primary_key=True)
    body = models.JSONField(default=dict)

    @staticmethod
    def spec_id_to_identifier(spec_id):
        assert spec_id.startswith(Component.SPEC_PREFIX)
        return spec_id.replace(Component.SPEC_PREFIX, "", 1)

    # TODO: should be an object manager
    @staticmethod
    def get_from_spec_id(spec_id):
        identifier = Component.spec_id_to_identifier(spec_id)
        return Component.objects.get(identifier=identifier)

    @property
    def model_input_run_identifier(self):
        input_id = self.body["model_input_run"]
        if input_id is None:
            return input_id
        return Component.spec_id_to_identifier(input_id)

    @property
    def environment_identifier(self):
        return self.body["data"]["tags"]["environment_identifier"]

    @property
    def agent_identifier(self):
        return self.body["data"]["tags"]["agent_identifier"]

    @property
    def run_name(self):
        return self.body["data"]["tags"]["mlflow.runName"]

    @property
    def mean_reward(self):
        return self.body["data"]["metrics"]["mean_reward"]

    @property
    def training_episode_count(self):
        return self.body["data"]["metrics"]["training_episode_count"]

    @property
    def training_step_count(self):
        return self.body["data"]["metrics"]["training_step_count"]

    @property
    def start_time(self):
        start_time_ms = int(self.body["info"]["start_time"])
        start_time = datetime.datetime.fromtimestamp(start_time_ms / 1000)
        return start_time.strftime("%m/%d/%y %H:%m")

    @property
    def environment(self):
        return Component.objects.get(identifier=self.environment_identifier)

    @property
    def agent(self):
        return Component.objects.get(identifier=self.agent_identifier)

    @property
    def agent_name(self):
        instance = Component.get_from_spec_id(self.agent.body["instance_of"])
        return instance.body["name"]

    @staticmethod
    def create_from_request_data(request_data: QueryDict):
        # get mutable version of request so that we can decode json fields. Per
        # https://docs.djangoproject.com/en/4.0/ref/request-response/#querydict-objects
        data = request_data.copy()
        identifier = data[PCSComponent.IDENTIFIER_KEY]
        encoded_body = data[WebRegistry.SPEC_RESPONSE_BODY_KEY]
        flat_spec = json.decoder.JSONDecoder().decode(encoded_body)
        # TODO - When we have accounts, we need to check the the user
        #        has permission to create a new version of this Module
        #        (i.e. if the name already exists but not the version).
        component, created = Component.objects.get_or_create(
            identifier=identifier, defaults={"body": flat_spec}
        )
        print(f"Got Component {component}, created: {created}")
        return component

    @staticmethod
    def agent_run_dags() -> Tuple:
        agent_runs = Component.objects.filter(body__type="AgentRun")
        run_obj_by_id = {}
        env_obj_by_id = {}
        run_to_env_id = {}

        # {env_id: {agent_id: [ids_of_runs_without_input_parents]}}
        root_run_ids = defaultdict(lambda: defaultdict(list))
        run_graph = {}  # {parent_id: child_id}
        for run in agent_runs:
            run_id = run.identifier
            env_id = run.environment_identifier
            agent_id = run.agent_identifier
            run_obj_by_id[run_id] = run
            env_obj_by_id[env_id] = run.environment
            run_to_env_id[run_id] = env_id

            # Store our roots, which we'll use to for traversal later
            if not run.model_input_run_identifier:
                root_run_ids[env_id][agent_id].append(run_id)
            # Store graph edges from parent to child (opposite of how they are)
            else:
                run_graph[run.model_input_run_identifier] = run_id

        # Find the terminal node for every root_run (might be itself)
        terminals = defaultdict(list)
        node_to_root = {}
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
    def agent_run_dag(identifier, learn_only=False) -> List:
        (
            run_map,
            env_map,
            root_ids,
            term_ids,
            n2r,
            graph,
        ) = Component.agent_run_dags()
        print(f"run_id_map.keys(): {run_map.keys()}")
        ident = n2r[identifier]
        res = [run_map[ident]]
        while ident in graph:
            ident = graph[ident]
            run_type = run_map[ident].data.get("tags", {}).get("run_type", "")
            if not learn_only or run_type == "learn":
                res.append(run_map[ident])
        return res
