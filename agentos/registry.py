import abc
import os
import yaml
import json
import pprint
import shutil
import tarfile
import tempfile
import requests
from pathlib import Path
from typing import Dict, Sequence, Union, TYPE_CHECKING
from dotenv import load_dotenv
from agentos.identifiers import ComponentIdentifier, RunIdentifier
from agentos.specs import (
    flatten_spec,
    RepoSpec,
    ComponentSpec,
    NestedComponentSpec,
    RunSpec,
    RunCommandSpec,
)

if TYPE_CHECKING:
    from agentos.component import Component
    from agentos.run import Run

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

    @classmethod
    def from_default(cls):
        if not hasattr(cls, "_default_registry"):
            cls._default_registry = WebRegistry(AOS_WEB_API_ROOT)
        return cls._default_registry

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        raise NotImplementedError

    def to_yaml(self, filename: str) -> None:
        with open(filename, "w") as file:
            yaml.dump(self.to_dict(), file)

    @abc.abstractmethod
    def get_component_specs(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> NestedComponentSpec:
        """
        Return dictionary of component specs in this Registry, optionally
        filtered by name and/or version; or None if none are found.

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
        filtered by name, version, or both. If no matching components are
        found, an empty dictionary is returned.
        """
        raise NotImplementedError

    def get_component_spec(
        self,
        name: str,
        version: str = None,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> ComponentSpec:
        """
        Returns the component spec with ``name`` and ``version``, if it exists,
        or raise an Error if it does not. A component's name and version are
        defined as its identifier's name and version.

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
        :param flatten: If True, flatten the outermost 2 layers of nested
            dicts into a single dict. In an unflattened component spec, the
            outermost dict is from identifier (which is a string in the format
            of name[==version]) Component component properties (class_name,
            repo, etc.). In a flattened Component spec, the name and version
            are included in the same dictionary as the class_name, repo,
            dependencies, etc.
        :param error_if_not_found: Set to False to return an empty dict in
            the case that a matching component is not found in this registry.
        :returns: a ComponentSpec (i.e. a dict) matching the filter criteria
            provided, else throw an error.
        """
        components = self.get_component_specs(name, version)
        if len(components) == 0:
            if error_if_not_found:
                raise LookupError(
                    f"This registry does not contain any components that "
                    f"match your filter criteria: name:'{name}', "
                    f"version:'{version}'."
                )
            else:
                return {}
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
        if flatten:
            component_tuple = components.popitem()
            identifier_str = component_tuple[0]
            identifier = ComponentIdentifier.from_str(identifier_str)
            flat_component_dict = component_tuple[1]
            flat_component_dict["name"] = identifier.name
            flat_component_dict["version"] = identifier.version
            return flat_component_dict
        return components

    def get_component_spec_by_id(
        self,
        identifier: Union[ComponentIdentifier, str],
        flatten: bool = False,
    ) -> ComponentSpec:
        identifier = ComponentIdentifier.from_str(str(identifier))
        return self.get_component_spec(
            identifier.name, identifier.version, flatten=flatten
        )

    @abc.abstractmethod
    def get_repo_spec(self, repo_id: str, flatten: bool = False) -> RepoSpec:
        raise NotImplementedError

    @abc.abstractmethod
    def get_run_spec(
        self, run_id: RunIdentifier, flatten: bool = False
    ) -> RunSpec:
        raise NotImplementedError

    def get_run_command_spec(
        self, run_command_id: str, flatten: bool = False
    ) -> RunCommandSpec:
        raise NotImplementedError

    @abc.abstractmethod
    def get_registries(self) -> Sequence:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component_spec(self, component_spec: NestedComponentSpec) -> None:
        """
        Adds a component spec to this registry. *This does not add any
        Registry Objects* to this registry. Those must be handled explicitely.

        Typically, to register a component, it's easier to use the higher
        level function Component.register(registry).

        :param component_spec: The ``ComponentSpec`` to register.
        """
        raise NotImplementedError

    def add_component(
        self, component: "Component", recurse: bool = True, force: bool = False
    ) -> None:
        component.to_registry(self, recurse=recurse, force=force)

    @abc.abstractmethod
    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_run_spec(self, run_spec: RunSpec) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_run_command_spec(self, run_command_spec: RunCommandSpec) -> None:
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
        if "run_commands" not in self._registry.keys():
            self._registry["run_commands"] = {}
        if "registries" not in self._registry.keys():
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

    def get_repo_spec(self, repo_id: str, flatten: bool = False) -> "RepoSpec":
        inner = self._registry["repos"][repo_id]
        if flatten:
            inner.update({"identifier": repo_id})
            return inner
        else:
            return {repo_id: inner}

    def get_run_spec(
        self, run_id: RunIdentifier, flatten: bool = False
    ) -> RunSpec:
        inner = {run_id: self._registry["runs"][run_id]}
        if flatten:
            inner.update({"identifier": inner})
            return inner
        else:
            return {run_id: inner}

    def get_run_command_spec(
        self, run_command_id: str, flatten: bool = False
    ) -> RunCommandSpec:
        inner = self._registry["run_commands"][run_command_id]
        if flatten:
            inner.update({"identifier": run_command_id})
            return inner
        else:
            return {run_command_id: inner}

    def get_registries(self) -> Sequence[Registry]:
        return self._registry["registries"]

    def add_component_spec(self, component_spec: NestedComponentSpec) -> None:
        self._registry["components"].update(component_spec)

    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        self._registry["repos"].update(repo_spec)

    def add_run_spec(self, run_spec: RunSpec) -> None:
        self._registry["runs"].update(run_spec)

    def add_run_command_spec(self, run_command_spec: RunCommandSpec) -> None:
        self._registry["run_commands"].update(run_command_spec)

    def to_dict(self) -> Dict:
        return self._registry


class WebRegistry(Registry):
    """
    A web-server backed Registry.
    """

    def __init__(self, root_api_url: str, base_dir: str = None):
        self.root_api_url = root_api_url
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
        url_filter_str = ""
        if filter_by_name:
            url_filter_str += f"name={filter_by_name}"
        if filter_by_version:
            if url_filter_str:
                url_filter_str += "&"
            url_filter_str += f"version={filter_by_version}"
        if url_filter_str:
            url_filter_str = f"?{url_filter_str}"
        component_url = f"{self.root_api_url}/components{url_filter_str}"
        print(f"trying {component_url}")
        component_response = requests.get(component_url)
        assert component_response.status_code == 200
        json_results = json.loads(component_response.content)
        component_specs = {}
        for c_dict in json_results["results"]:
            identifier = f"{c_dict['name']}=={c_dict['version']}"
            component_specs[identifier] = {
                "repo": c_dict["repo"],
                "file_path": c_dict["file_path"],
                "class_name": c_dict["class_name"],
                "instantiate": c_dict["instantiate"],
                "dependencies": c_dict["dependencies"],
            }
        return component_specs

    def get_default_component(self, name: str):
        raise NotImplementedError

    def get_repo_spec(self, repo_id: str, flatten: bool = False) -> "RepoSpec":
        repo_url = f"{self.root_api_url}/repos?identifier={repo_id}"
        print(f"trying {repo_url}")
        repo_response = requests.get(repo_url)
        assert repo_response.status_code == 200
        json_results = json.loads(repo_response.content)
        assert len(json_results["results"]) <= 1, (
            f"{len(json_results['results'])} repos with identifier {repo_id} "
            f"were returned by {repo_url} but only 0 or 1 should have been."
        )
        repo_spec = {}
        for r_dict in json_results["results"]:
            inner = {
                "identifier": r_dict["identifier"],
                "type": r_dict["type"],
            }
            if r_dict["type"] == "github":
                inner["url"] = r_dict["url"]
            if flatten:
                repo_spec["identifier"] = r_dict["identifier"]
                repo_spec.update(inner)
            else:
                repo_spec[r_dict["identifier"]] = inner
        return repo_spec

    def get_run_command_spec(
        self, run_command_id: str, flatten: bool = False
    ) -> RunCommandSpec:
        raise NotImplementedError

    def get_run_spec(
        self, run_id: RunIdentifier, flatten: bool = False
    ) -> RunSpec:
        if flatten:
            raise NotImplementedError
        run_url = f"{self.root_api_url}/runs/{run_id}"
        run_response = requests.get(run_url)
        return json.loads(run_response.content)

    def get_registries(self) -> Sequence:
        raise NotImplementedError

    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        url = f"{self.root_api_url}/repos/"
        print("Sending HTTP POST with data:")
        print(flatten_spec(repo_spec))
        response = requests.post(url, data=flatten_spec(repo_spec))
        self._check_response(response)
        result = json.loads(response.content)
        print("\nadd_repo_spec http response results:")
        pprint.pprint(result)
        print()

    def to_dict(self) -> Dict:
        raise Exception("to_dict() is not supported on WebRegistry.")

    def add_component_spec(self, component_spec: NestedComponentSpec) -> None:
        """
        Register a Component Spec. Component spec must be frozen.
        :param component_spec: A frozen component spec.
        """
        url = f"{self.root_api_url}/components/ingest_spec/"
        data = {"components.yaml": yaml.dump(component_spec)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        print("\nadd_component_spec http response results:")
        pprint.pprint(result)
        print()
        return result

    def add_run_spec(self, run_data: RunSpec) -> Sequence:
        url = f"{self.root_api_url}/runs/"
        data = {"run_data": yaml.dump(run_data)}
        response = requests.post(url, data=data)
        self._check_response(response)
        result = json.loads(response.content)
        return result

    def add_run_artifacts(
        self, run_id: int, run_artifact_paths: Sequence[str]
    ) -> Sequence:
        try:
            tmp_dir_path = Path(tempfile.mkdtemp())
            tar_gz_path = tmp_dir_path / f"run_{run_id}_artifacts.tar.gz"
            with tarfile.open(tar_gz_path, "w:gz") as tar:
                for artifact_path in run_artifact_paths:
                    tar.add(artifact_path, arcname=artifact_path.name)
            files = {"tarball": open(tar_gz_path, "rb")}
            url = f"{self.root_api_url}/runs/{run_id}/upload_artifact/"
            response = requests.post(url, files=files)
            result = json.loads(response.content)
            return result
        finally:
            shutil.rmtree(tmp_dir_path)

    def add_run_command_spec(self, run_command_spec: RunCommandSpec) -> None:
        raise NotImplementedError

    def get_run(self, run_id: str) -> "Run":
        from agentos.run import Run

        return Run.from_registry(self, run_id)
