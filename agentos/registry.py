import abc
import os
import yaml
import json
import mlflow
import pprint
import shutil
import tarfile
import tempfile
import requests
from component import Component
from pathlib import Path
from typing import Dict
from typing import List
from dotenv import load_dotenv

from agentos.utils import MLFLOW_EXPERIMENT_ID, _handle_acme_r2d2, \
    _handle_sb3_agent

# add USE_LOCAL_SERVER=True to .env to talk to local server
load_dotenv()

AOS_WEB_BASE_URL = "https://aos-web.herokuapp.com"
if os.getenv("USE_LOCAL_SERVER", False) == "True":
    AOS_WEB_BASE_URL = "http://localhost:8000"
AOS_WEB_API_EXTENSION = "/api/v1"

AOS_WEB_API_ROOT = f"{AOS_WEB_BASE_URL}{AOS_WEB_API_EXTENSION}"


class Registry(abc.ABC):
    @staticmethod
    def from_dict(input_dict: Dict) -> "Registry":
        return InMemoryRegistry(input_dict)

    @property
    @abc.abstractmethod
    def component_specs(self) -> Dict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def repo_specs(self) -> Dict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def run_specs(self) -> Dict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def fallback_registries(self) -> List:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component(self, component: Component) -> None:
        raise NotImplementedError


class InMemoryRegistry(Registry):
    """
    This encapsulates interactions with an external registry that contains
    information about publicly-available Components.
    """

    def __init__(self, input_dict: Dict = None):
        self._registry = input_dict if input_dict else DUMMY_DEV_REGISTRY_DICT

    @property
    def component_specs(self) -> Dict:
        return self._registry.get("components", {})

    @property
    def repo_specs(self) -> Dict:
        return self._registry.get("repos", {})

    @property
    def run_specs(self) -> Dict:
        return self._registry.get("runs", {})

    @property
    def fallback_registries(self) -> List:
        return self._registry.get("fallback_registries", [])

    def add_component(self, component: Component) -> None:
        self._registry[component.identifer] = component


class WebRegistry(Registry):
    @staticmethod
    def _check_response(self, response):
        if not response.ok:
            content = json.loads(response.content)
            if type(content) == list:
                content = content[0]
            raise Exception(content)

    def push_component_spec(self, frozen_spec: Dict) -> Dict:
        url = f"{AOS_WEB_API_ROOT}/components/ingest_spec/"
        data = {"components.yaml": yaml.dump(frozen_spec)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        print("\nResults:")
        pprint.pprint(result)
        print()
        return result

    def push_run_spec(self, run_data: Dict) -> List:
        url = f"{AOS_WEB_API_ROOT}/runs/"
        data = {"run_data": yaml.dump(run_data)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        return result

    def push_run_artifacts(run_id: int, run_artifacts: List) -> List:
        try:
            tmp_dir_path = Path(tempfile.mkdtemp())
            tar_gz_path = tmp_dir_path / f"run_{run_id}_artifacts.tar.gz"
            with tarfile.open(tar_gz_path, "w:gz") as tar:
                for artifact_path in run_artifacts:
                    tar.add(artifact_path, arcname=artifact_path.name)
            files = {"tarball": open(tar_gz_path, "rb")}
            url = f"{AOS_WEB_API_ROOT}/runs/{run_id}/upload_artifact/"
            response = requests.post(url, files=files)
            result = json.loads(response.content)
            return result
        finally:
            shutil.rmtree(tmp_dir_path)

    def get_run(self, run_id: int) -> None:
        from agentos.tracker import AgentTracker

        run_url = f"{AOS_WEB_API_ROOT}/runs/{run_id}"
        run_response = requests.get(run_url)
        run_data = json.loads(run_response.content)
        with open("parameter_set.yaml", "w") as param_file:
            param_file.write(yaml.safe_dump(run_data["parameter_set"]))

        root_response = requests.get(run_data["root_link"])
        root_data = json.loads(root_response.content)

        rerun_cmd = (
            f'agentos run {root_data["name"]}=={root_data["version"]} '
            f'--entry-point {run_data["entry_point"]} '
            f"--param-file parameter_set.yaml"
        )
        with open("README.md", "w") as readme_file:
            readme_file.write("## Rerun this agent\n\n```\n")
            readme_file.write(rerun_cmd)
            readme_file.write("\n```")
        spec_url = f"{run_url}/root_spec"
        spec_response = requests.get(spec_url)
        spec_dict = json.loads(spec_response.content)
        with open("agentos.yaml", "w") as file_out:
            file_out.write(yaml.safe_dump(spec_dict))
        try:
            tar_url = f"{run_url}/download_artifact"
            tmp_dir_path = Path(tempfile.mkdtemp())
            requests.get(tar_url)
            tarball_response = requests.get(tar_url)
            tarball_name = "artifacts.tar.gz"
            tarball_path = tmp_dir_path / tarball_name
            with open(tarball_path, "wb") as f:
                f.write(tarball_response.content)
            tar = tarfile.open(tarball_path)
            tar.extractall(path=tmp_dir_path)
            mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
            mlflow.set_tag(AgentTracker.RUN_TYPE_TAG, AgentTracker.LEARN_KEY)
            mlflow.log_metric(
                "episode_count", run_data["metrics"]["training_episode_count"]
            )
            mlflow.log_metric(
                "step_count", run_data["metrics"]["training_step_count"]
            )
            mlflow.end_run()
            mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
            mlflow.set_tag(AgentTracker.RUN_TYPE_TAG, AgentTracker.RESTORE_KEY)
            for file_name in os.listdir(tmp_dir_path):
                if file_name == tarball_name:
                    continue
                file_path = tmp_dir_path / file_name
                mlflow.log_artifact(file_path)
            for name, value in run_data["metrics"].items():
                mlflow.log_metric(name, value)
            mlflow.end_run()
            print("\nRerun agent as follows:")
            print(rerun_cmd)
            print()
        finally:
            shutil.rmtree(tmp_dir_path)


DUMMY_DEV_REGISTRY_DICT = {
    "components": {
        "acme_cartpole==nj_registry_2next": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/environment.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_agent==nj_registry_2next": {
            "class_name": "AcmeR2D2Agent",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
                "policy": "acme_r2d2_policy==nj_registry_2next",
                "tracker": "acme_tracker==nj_registry_2next",
                "trainer": "acme_r2d2_trainer==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/agent.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_dataset==nj_registry_2next": {
            "class_name": "ReverbDataset",
            "dependencies": {
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/dataset.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_network==nj_registry_2next": {
            "class_name": "R2D2Network",
            "dependencies": {
                "environment": "acme_cartpole==nj_registry_2next",
                "tracker": "acme_tracker==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/network.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_policy==nj_registry_2next": {
            "class_name": "R2D2Policy",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/policy.py",
            "repo": "dev_repo",
        },
        "acme_r2d2_trainer==nj_registry_2next": {
            "class_name": "R2D2Trainer",
            "dependencies": {
                "dataset": "acme_r2d2_dataset==nj_registry_2next",
                "environment": "acme_cartpole==nj_registry_2next",
                "network": "acme_r2d2_network==nj_registry_2next",
            },
            "file_path": "example_agents/acme_r2d2/trainer.py",
            "repo": "dev_repo",
        },
        "acme_tracker==nj_registry_2next": {
            "class_name": "AcmeTracker",
            "dependencies": {},
            "file_path": "example_agents/acme_r2d2/../acme_dqn/tracker.py",
            "repo": "dev_repo",
        },
        "sb3_cartpole==nj_registry_2next": {
            "class_name": "CartPole",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/environment.py",
            "repo": "dev_repo",
        },
        "sb3_ppo_agent==nj_registry_2next": {
            "class_name": "SB3PPOAgent",
            "dependencies": {
                "environment": "sb3_cartpole==nj_registry_2next",
                "tracker": "sb3_tracker==nj_registry_2next",
            },
            "file_path": "example_agents/sb3_agent/agent.py",
            "repo": "dev_repo",
        },
        "sb3_tracker==nj_registry_2next": {
            "class_name": "SB3Tracker",
            "dependencies": {},
            "file_path": "example_agents/sb3_agent/tracker.py",
            "repo": "dev_repo",
        },
    },
    "latest_refs": {
        "acme_cartpole": "nj_registry_2next",
        "acme_r2d2_agent": "nj_registry_2next",
        "acme_r2d2_dataset": "nj_registry_2next",
        "acme_r2d2_network": "nj_registry_2next",
        "acme_r2d2_policy": "nj_registry_2next",
        "acme_r2d2_trainer": "nj_registry_2next",
        "acme_tracker": "nj_registry_2next",
        "sb3_cartpole": "nj_registry_2next",
        "sb3_ppo_agent": "nj_registry_2next",
        "sb3_tracker": "nj_registry_2next",
    },
    "repos": {
        "dev_repo": {
            "type": "github",
            "url": "https://github.com/nickjalbert/agentos",
        }
    },
}


def generate_dummy_dev_registry():
    registry = {}
    VERSION_STRING = "nj_registry_2next"
    r2d2 = _handle_acme_r2d2(VERSION_STRING)
    _merge_registry_dict(registry, r2d2)
    sb3 = _handle_sb3_agent(VERSION_STRING)
    _merge_registry_dict(registry, sb3)
    pprint.pprint(registry)
    return registry


def _merge_registry_dict(a, b):
    for key, val in b.items():
        tmp = a.get(key, {})
        tmp.update(val)
        a[key] = tmp