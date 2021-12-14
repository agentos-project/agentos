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
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING
from dotenv import load_dotenv

if TYPE_CHECKING:
    from agentos.component import Component
from agentos.utils import MLFLOW_EXPERIMENT_ID

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

    @staticmethod
    def from_yaml(yaml_file: str) -> "Registry":
        with open(yaml_file) as file_in:
            config = yaml.safe_load(file_in)
        return InMemoryRegistry(
            config, base_dir=Path(yaml_file).parent
        )

    @abc.abstractmethod
    def components(
        self,
        filter_by_name: str = None,
        filter_by_version: str = None,
    ) -> Dict["Component.Identifier", Dict]:
        """
        Return dictionary of component specs in this Registry.
        Each Component Spec is itself a dict mapping Component.Identifier to a
        dict of properties that define the Component.

        Optionally, filter the list to match all filter strings provided.
        Filters can be provided on name, version, or both.
        If this registry contains zero component specs that match
        the filter criteria (if any), then an empty dictionary is returned.
        If ``filter_by_name`` and ``filter_by_version`` are provided,
        then 0 or 1 components will be returned.

        :param filter_by_name: return only components with this name.
        :param filter_by_version: return only components with this version.

        :returns: A dictionary of components in this registry, optionally
        filtered by name, version, or both.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def repos(self) -> Dict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def runs(self) -> Dict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def fallback_registries(self) -> List:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component(self, component: "Component") -> None:
        raise NotImplementedError

    def __init__(self, base_dir: str = None):
        self.base_dir = (
            base_dir if base_dir else "."
        )  # Used for file-backed Registry types.


class InMemoryRegistry(Registry):
    """
    This encapsulates interactions with an external registry that contains
    information about publicly-available Components.
    """

    def __init__(self, input_dict: Dict = None, base_dir: str = None):
        super().__init__(base_dir)
        self._registry = input_dict if input_dict else {}
        if "components" not in self._registry.keys():
            self._registry["components"] = {}
        if "repos" not in self._registry.keys():
            self._registry["repos"] = {}
        if "runs" not in self._registry.keys():
            self._registry["runs"] = {}
        if "fallback_registries" not in self._registry.keys():
            self._registry["registries"] = []

    def component(self, component_id: "Component.Identifier"):
        """Returns the component with ``component_id``, if it exists."""
        return self._registry["components"][component_id]

    def components(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> Dict["Component.Identifier", Dict]:
        if filter_by_name or filter_by_version:
            try:
                from agentos.component import Component

                components = {}
                for k, v in self._registry["components"].items():
                    candidate_id = Component.Identifier.from_str(k)
                    passes_filter = True
                    if filter_by_name and candidate_id.name != filter_by_name:
                        passes_filter = False
                    if (
                        filter_by_version
                        and candidate_id.version != filter_by_version
                    ):
                        passes_filter = False
                    if passes_filter:
                        components[k] = v
                return components
            except KeyError:
                return {}
        return self._registry["components"]

    @property
    def repos(self) -> Dict:
        return self._registry["repos"]

    @property
    def runs(self) -> Dict:
        return self._registry["runs"]

    @property
    def fallback_registries(self) -> List:
        return self._registry["fallback_registries"]

    def add_component(self, component: "Component") -> None:
        print(component)
        self._registry["components"][component.identifier] = component
        self._registry["repos"][component.repo.name] = component.repo


class WebRegistry(Registry):
    @staticmethod
    def _check_response(self, response):
        if not response.ok:
            content = json.loads(response.content)
            if type(content) == list:
                content = content[0]
            raise Exception(content)

    def __init__(self, root_url: str, base_dir: str = None):
        self.root_url = root_url
        self.base_dir = (
            base_dir if base_dir else "."
        )  # Used for file-backed Registry types.

    def components(
            self,
            filter_by_name: str = None,
            filter_by_version: str = None,
    ) -> Dict["Component.Identifier", Dict]:
        raise NotImplementedError

    @property
    def repos(self) -> Dict:
        raise NotImplementedError

    @property
    def runs(self) -> Dict:
        raise NotImplementedError

    @property
    def fallback_registries(self) -> List:
        raise NotImplementedError

    def add_component(self, component: "Component") -> None:
        raise NotImplementedError

    def push_component_spec(self, frozen_spec: Dict) -> Dict:
        url = f"{self.root_url}/components/ingest_spec/"
        data = {"components.yaml": yaml.dump(frozen_spec)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        print("\nResults:")
        pprint.pprint(result)
        print()
        return result

    def push_run_data(self, run_data: Dict) -> List:
        url = f"{self.root_url}/runs/"
        data = {"run_data": yaml.dump(run_data)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        return result

    def push_run_artifacts(self, run_id: int, run_artifacts: List) -> List:
        try:
            tmp_dir_path = Path(tempfile.mkdtemp())
            tar_gz_path = tmp_dir_path / f"run_{run_id}_artifacts.tar.gz"
            with tarfile.open(tar_gz_path, "w:gz") as tar:
                for artifact_path in run_artifacts:
                    tar.add(artifact_path, arcname=artifact_path.name)
            files = {"tarball": open(tar_gz_path, "rb")}
            url = f"{self.root_url}/runs/{run_id}/upload_artifact/"
            response = requests.post(url, files=files)
            result = json.loads(response.content)
            return result
        finally:
            shutil.rmtree(tmp_dir_path)

    def get_run(self, run_id: int) -> None:
        from agentos.tracker import AgentTracker

        run_url = f"{self.root_url}/runs/{run_id}"
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

web_registry = WebRegistry(AOS_WEB_API_ROOT)
