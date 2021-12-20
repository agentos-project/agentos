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
from typing import Dict, List, Union
from dotenv import load_dotenv
from agentos.component_identifier import ComponentIdentifier
from agentos.utils import MLFLOW_EXPERIMENT_ID
from agentos.specs import RepoSpec, ComponentSpec, NestedComponentSpec

# add USE_LOCAL_SERVER=True to .env to talk to local server
load_dotenv()

AOS_WEB_BASE_URL = "https://aos-web.herokuapp.com"
if os.getenv("USE_LOCAL_SERVER", False) == "True":
    AOS_WEB_BASE_URL = "http://localhost:8000"
AOS_WEB_API_EXTENSION = "/api/v1"

AOS_WEB_API_ROOT = f"{AOS_WEB_BASE_URL}{AOS_WEB_API_EXTENSION}"


class Registry(abc.ABC):
    def __init__(self, base_dir: str = None):
        self.base_dir = (
            base_dir if base_dir else "."
        )  # Used for file-backed Registry types.

    @staticmethod
    def from_dict(input_dict: Dict) -> "Registry":
        return InMemoryRegistry(input_dict)

    @staticmethod
    def from_yaml(yaml_file: str) -> "Registry":
        with open(yaml_file) as file_in:
            config = yaml.safe_load(file_in)
        return InMemoryRegistry(config, base_dir=str(Path(yaml_file).parent))

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        raise NotImplementedError

    @abc.abstractmethod
    def get_component_specs(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> NestedComponentSpec:
        """
        Return dictionary of component specs in this Registry.
        Each Component Spec is itself a dict mapping ComponentIdentifier to a
        dict of properties that define the Component.

        Optionally, filter the list to match all filter strings provided.
        Filters can be provided on name, version, or both.
        If this registry contains zero component specs that match
        the filter criteria (if any), then an empty dictionary is returned.
        If ``filter_by_name`` and ``filter_by_version`` are provided,
        then 0 or 1 components will be returned.

        :param filter_by_name: return only components with this name.
        :param filter_by_version: return only components with this version.
        :param include_id_in_contents: add ``name`` and ``version`` fields to
               innermost dict of the ComponentSpec Dict. This denormalizes the
               spec by duplicating the ``name`` and ``version`` which are
               already included via the ComponentIdentifier Dict key.

        :returns: A dictionary of components in this registry, optionally
        filtered by name, version, or both.
        """
        raise NotImplementedError

    def get_component_spec(
        self, name: str, version: str = None, flattened: bool = True
    ) -> ComponentSpec:
        """
        Returns the component spec with ``name`` and ``version``, if it exists.
        A component's name and version are defined as its identifier's name
        and version.

        Registries are not allowed to contain multiple Components with the same
        identifier. The Registry abstract base class does not enforce that all
        Components have a version (version can be None) though some
        sub-classes, such as web service backed registries, may choose to
        enforce that constraint.

        When version is unspecified or None, this function assumes that a
        Component ``c`` exists where ``c.name == name`` and ``c.version is
        None``, and throws an error otherwise.

        Subclasses of Registry may choose to provide their own (more elaborate)
        semantics for "default components". E.g., since WebRegistry does not
        allow non-versioned components, it defines its own concept of a default
        component by maintaining a separate map from component name to
        a specific version of the component, and it allows that mapping to be
        updated by users.

        :param name: The name of the component to fetch.
        :param version: Optional version of the component to fetch.
        :param flattened: If True, flatten the outermost 2 layers of nested
                          dicts into a single dict. In an unflattened component
                          spec, the outermost dict is from identifier
                          (which is a string in the format of name[==version])
                          Component component properties (class_name, repo,
                          etc.). In a flattened Component spec, the name and
                          version are included in the same dictionary as the
                          class_name, repo, dependencies, etc.
        """
        components = self.get_component_specs(name, version)
        print(f"components: {components}")
        if len(components) == 0:
            raise LookupError(
                f"This registry does not contain any components that match "
                f"your filter criteria: name:'{name}', version:'{version}'."
            )
        if len(components) > 1:
            versions = [
                ComponentIdentifier.from_str(c_id).version
                for c_id in components.keys()
            ]
            version_str = "\n - ".join(versions)
            raise LookupError(
                f"This registry contains more than one component with "
                f"the name {name}. Please specify one of the following "
                f"versions:\n - {version_str}"
            )
        if flattened:
            component_tuple = components.popitem()
            identifier_str = component_tuple[0]
            identifier = ComponentIdentifier.from_str(identifier_str)
            print(f"identifier: {identifier}")
            flat_component_dict = component_tuple[1]
            flat_component_dict["name"] = identifier.name
            flat_component_dict["version"] = identifier.version
            print(f"returning flat_component: {flat_component_dict}")
            return flat_component_dict
        return components

    def get_component_spec_by_id(
        self, identifier: Union[ComponentIdentifier, str]
    ) -> ComponentSpec:
        identifier = ComponentIdentifier.from_str(str(identifier))
        return self.get_component_spec(identifier.name, identifier.version)

    @abc.abstractmethod
    def get_repo_spec(self, repo_id: str) -> "RepoSpec":
        raise NotImplementedError

    @abc.abstractmethod
    # TODO: replace Dict return type with RunSpec once we have it.
    def get_run_spec(self, run_id: str) -> Dict:
        raise NotImplementedError

    @abc.abstractmethod
    def get_fallback_registries(self) -> List:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component_spec(self, component_spec: "ComponentSpec") -> None:
        """
        Adds a component spec to this registry. *This does not add any
        Registry Objects* to this registry. Those must be handled explicitely.

        Typically, to register a component, it's easier to use the higher
        level function Component.register(registry).

        :param component_spec: The ``ComponentSpec`` to register.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        raise NotImplementedError


class InMemoryRegistry(Registry):
    """
    A mutable in-memory registry.
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

    def get_component_specs(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> NestedComponentSpec:
        if filter_by_name or filter_by_version:
            try:
                components = {}
                for k, v in self._registry["components"].items():
                    candidate_id = ComponentIdentifier.from_str(k)
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

    def get_repo_spec(self, repo_id: str) -> "RepoSpec":
        return self._registry["repos"][repo_id]

    def get_run_spec(self, run_id: str) -> Dict:
        return self._registry["runs"][run_id]

    def get_fallback_registries(self) -> List[Registry]:
        return self._registry["fallback_registries"]

    def add_component_spec(self, component_spec: "ComponentSpec") -> None:
        self._registry["components"].update(component_spec)

    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        self._registry["repos"].update(repo_spec)

    def to_dict(self) -> Dict:
        return self._registry


class WebRegistry(Registry):
    """
    A web-server backed Registry.
    """

    def __init__(self, root_url: str, base_dir: str = None):
        self.root_url = root_url
        self.base_dir = (
            base_dir if base_dir else "."
        )  # Used for file-backed Registry types.

    @staticmethod
    def _check_response(response):
        if not response.ok:
            content = json.loads(response.content)
            if type(content) == list:
                content = content[0]
            raise Exception(content)

    def get_component_specs(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> NestedComponentSpec:
        raise NotImplementedError

    def get_default_component(self, name: str):
        raise NotImplementedError

    def get_repo_spec(self, repo_id: str) -> "RepoSpec":
        raise NotImplementedError

    def get_run_spec(self, run_id: str) -> Dict:
        raise NotImplementedError

    def get_fallback_registries(self) -> List:
        raise NotImplementedError

    def add_component_spec(self, component_spec: "ComponentSpec") -> None:
        self.push_component_spec(component_spec)

    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        raise NotImplementedError

    def to_dict(self) -> Dict:
        raise NotImplementedError

    def push_component_spec(self, frozen_spec: "ComponentSpec") -> Dict:
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
