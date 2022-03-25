import abc
import json
import logging
import os
import pprint
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Sequence, Tuple, Union

import requests
import yaml
from dotenv import load_dotenv

from pcs.identifiers import (
    ComponentIdentifier,
    RepoIdentifier,
    RunCommandIdentifier,
    RunIdentifier,
)
from pcs.specs import (
    ComponentSpec,
    NestedComponentSpec,
    RepoSpec,
    RunCommandSpec,
    RunSpec,
    flatten_spec,
    is_flat,
    json_encode_flat_spec_field,
    unflatten_spec,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pcs.component import Component
    from pcs.repo import Repo
    from pcs.run import Run

# add USE_LOCAL_SERVER=True to .env to talk to local server
load_dotenv()

AOS_WEB_BASE_URL = "https://aos-web.herokuapp.com"
if os.getenv("USE_LOCAL_SERVER", False) == "True":
    AOS_WEB_BASE_URL = "http://localhost:8000"
AOS_WEB_API_EXTENSION = "/api/v1"

AOS_WEB_API_ROOT = f"{AOS_WEB_BASE_URL}{AOS_WEB_API_EXTENSION}"
DEFAULT_REG_FILE = "components.yaml"


class Registry(abc.ABC):
    def __init__(self, base_dir: str = None):
        self.base_dir = (
            base_dir if base_dir else "."
        )  # Used for file-backed Registry types.

    @staticmethod
    def from_dict(input_dict: Dict) -> "Registry":
        return InMemoryRegistry(input_dict)

    @staticmethod
    def from_yaml(file_path: str) -> "Registry":
        with open(file_path) as file_in:
            config = yaml.safe_load(file_in)
        return InMemoryRegistry(config, base_dir=str(Path(file_path).parent))

    @classmethod
    def from_file_in_repo(
        cls, repo: "Repo", file_path: str, version: str, format: str = "yaml"
    ) -> "Registry":
        """
        Read in a registry file from an repo.

        :param repo: Repo to load registry file from.
        :param file_path: Path within Repo that registry is located, relative
            to the repo root.
        :param format: Optionally specify the format of the registry file.
        :return: a new Registry object.
        """
        assert (
            format == "yaml"
        ), "YAML is the only registry file format supported currently"
        return cls.from_yaml(repo.get_local_repo_dir(version) / file_path)

    @classmethod
    def from_repo_inferred(
        cls,
        repo: "Repo",
        version: str = None,
        py_file_suffixes: Tuple[str] = (".py", ".python"),
        requirements_file: str = "requirements.txt",
    ):
        from pcs.component import Component  # Avoid circular ref.

        reg = InMemoryRegistry()
        # get list of python files in Repo
        py_files = set()
        for suff in py_file_suffixes:
            found = repo.get_local_repo_dir(version=version).rglob(f"*{suff}")
            py_files = py_files.union(set(found))
        # create and register module, class, and class instance components
        for f in py_files:
            relative_path = f.relative_to(
                repo.get_local_repo_dir(version=version)
            )
            c_name = str(relative_path).replace(os.sep, "__")
            c_version = version if version else repo.default_version
            c_identifier = f"{c_name}=={c_version}" if c_version else c_name
            component_init_kwargs = {
                "repo": repo,
                "identifier": (f"module:{c_identifier}"),
                "file_path": str(relative_path),
                "instantiate": False,
            }
            if repo.get_local_file_path(
                requirements_file, version=c_version
            ).is_file():
                component_init_kwargs.update(
                    {"requirements_path": str(requirements_file)}
                )
            mod_component = Component(**component_init_kwargs)
            # TODO: add depenendencies to component for every import
            #       statement in the file (or just the ones at the
            #       module level?)
            reg.add_component(mod_component)
        return reg
        # TODO: finish this, add class components & class instance components?

    @classmethod
    def from_repo(cls, repo: "Repo"):
        """
        Get a registry from a Repo. If the Repo has a default registry file,
        use that, if not infer specs by inspecting the contents of the repo.
        """
        if DEFAULT_REG_FILE in repo:
            return cls.from_file_in_repo(DEFAULT_REG_FILE)
        return cls.from_repo_inferred(repo)

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
    def get_repo_spec(
        self,
        repo_id: RepoIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RepoSpec]:
        raise NotImplementedError

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
                  filtered by name, version, or both. If no matching
                  components are found, an empty dictionary is returned.
        """
        raise NotImplementedError

    def get_component_spec(
        self,
        name: str,
        version: str = None,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[ComponentSpec]:
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
                ComponentIdentifier(c_id).version for c_id in components.keys()
            ]
            version_str = "\n - ".join(versions)
            raise LookupError(
                f"This registry contains more than one component with "
                f"the name {name}. Please specify one of the following "
                f"versions:\n - {version_str}"
            )
        return flatten_spec(components) if flatten else components

    def get_component_spec_by_id(
        self,
        identifier: Union[ComponentIdentifier, str],
        flatten: bool = False,
    ) -> Optional[ComponentSpec]:
        identifier = ComponentIdentifier(identifier)
        return self.get_component_spec(
            identifier.name, identifier.version, flatten=flatten
        )

    def get_specs_transitively_by_id(
        self,
        identifier: Union[ComponentIdentifier, str],
        flatten: bool = True,
    ) -> (Sequence[ComponentSpec], Sequence[RepoSpec]):
        identifier = ComponentIdentifier(identifier)
        component_identifiers = [identifier]
        repo_specs = {}
        component_specs = {}
        while component_identifiers:
            c_id = component_identifiers.pop()
            c_spec = self.get_component_spec_by_id(c_id, flatten=flatten)
            inner_spec = c_spec if flatten else c_spec[c_id]
            component_specs[c_id] = c_spec
            repo_id = inner_spec["repo"]
            repo_spec = self.get_repo_spec(repo_id, flatten=flatten)
            repo_specs[repo_id] = repo_spec
            for d_id in inner_spec.get("dependencies", {}).values():
                component_identifiers.append(ComponentIdentifier(d_id))
        return list(component_specs.values()), list(repo_specs.values())

    def has_component_by_id(self, identifier: ComponentIdentifier) -> bool:
        try:
            self.get_component_spec_by_id(identifier)
        except LookupError:
            return False
        return True

    def has_component_by_name(self, name: str, version: str = None) -> bool:
        identifier = ComponentIdentifier(name, version)
        return self.has_component_by_id(identifier)

    def get_run_command_spec(
        self,
        run_command_id: RunCommandIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RunCommandSpec]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_run_spec(
        self,
        run_id: RunIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RunSpec]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_registries(self) -> Sequence:
        raise NotImplementedError

    @abc.abstractmethod
    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component_spec(self, component_spec: NestedComponentSpec) -> None:
        """
        Adds a component spec to this registry. *This does not add any
        Registry Objects* to this registry.

        To register a component, use the higher the level function
        Component.register(registry) or Registry.add_component().

        :param component_spec: The ``ComponentSpec`` to register.
        """
        raise NotImplementedError

    def add_component(
        self, component: "Component", recurse: bool = True, force: bool = False
    ) -> None:
        component.to_registry(self, recurse=recurse, force=force)

    @abc.abstractmethod
    def add_run_command_spec(self, run_command_spec: RunCommandSpec) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_run_spec(self, run_spec: RunSpec) -> None:
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

    def get_repo_spec(
        self,
        repo_id: RepoIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RepoSpec]:
        return self._get_spec(repo_id, "repos", flatten, error_if_not_found)

    def get_component_specs(
        self, filter_by_name: str = None, filter_by_version: str = None
    ) -> NestedComponentSpec:
        if filter_by_name or filter_by_version:
            try:
                components = {}
                for k, v in self._registry["components"].items():
                    candidate_id = ComponentIdentifier(k)
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

    def get_run_command_spec(
        self,
        run_command_id: RunCommandIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RunCommandSpec]:
        return self._get_spec(
            run_command_id, "run_commands", flatten, error_if_not_found
        )

    def get_run_spec(
        self,
        run_id: RunIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RunSpec]:
        return self._get_spec(run_id, "runs", flatten, error_if_not_found)

    def _get_spec(
        self,
        identifier: str,
        spec_type: str,
        flatten: bool,
        error_if_not_found: bool = True,
    ) -> Optional[Dict]:
        """
        Factor out common functionality for fetching specs from the
        internal represention of them. Because Components are special,
        (i.e., their identifiers can be versioned) they are handled
        differently.
        """
        assert spec_type in ["repos", "runs", "run_commands"]
        if identifier not in self._registry[spec_type]:
            if error_if_not_found:
                raise LookupError(
                    f"{self.__class__}l spec with identifier "
                    f"'{identifier}' not found."
                )
            else:
                return None
        spec = {identifier: self._registry[spec_type][identifier]}
        return flatten_spec(spec) if flatten else spec

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
    def _is_response_ok(
        response: requests.Response, error_if_not_found: bool = True
    ) -> bool:
        if response.ok:
            return True
        else:
            content = response.content
            try:
                content = json.loads(response.content)
                if type(content) == list:
                    content = content[0]
            except json.decoder.JSONDecodeError:
                try:
                    content = content.decode()
                except Exception:
                    pass
            if error_if_not_found:
                raise LookupError(response.text)
            else:
                return False

    def get_repo_spec(
        self,
        repo_id: RepoIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[RepoSpec]:
        return self._request_spec_from_web_server(
            "repo", repo_id, flatten, error_if_not_found
        )

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
        component_response = requests.get(component_url)
        assert component_response.status_code == 200
        json_results = json.loads(component_response.content)
        component_specs = {}
        for c_dict in json_results["results"]:
            identifier = f"{c_dict['name']}=={c_dict['version']}"
            dep_dict = {
                d["attribute_name"]: d["dependee"]
                for d in c_dict["depender_set"]
            }
            component_specs[identifier] = {
                "repo": c_dict["repo"],
                "file_path": c_dict["file_path"],
                "class_name": c_dict["class_name"],
                "instantiate": c_dict["instantiate"],
                "dependencies": dep_dict,
            }
        return component_specs

    def get_default_component(self, name: str):
        raise NotImplementedError

    def get_run_command_spec(
        self,
        run_command_id: RunCommandIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> RunCommandSpec:
        return self._request_spec_from_web_server(
            "runcommand", run_command_id, flatten, error_if_not_found
        )

    def get_run_spec(
        self,
        run_id: RunIdentifier,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> RunSpec:
        return self._request_spec_from_web_server(
            "run", run_id, flatten, error_if_not_found
        )

    def get_registries(self) -> Sequence:
        raise NotImplementedError

    def add_repo_spec(self, repo_spec: RepoSpec) -> None:
        self._post_spec_to_web_server("repo", repo_spec)

    def add_component_spec(self, component_spec: NestedComponentSpec) -> None:
        flat_spec = flatten_spec(component_spec)
        flat_spec = json_encode_flat_spec_field(flat_spec, "dependencies")
        self._post_spec_to_web_server("component", unflatten_spec(flat_spec))

    def add_run_command_spec(self, run_command_spec: RunCommandSpec) -> None:
        flat_spec = flatten_spec(run_command_spec)
        flat_spec = json_encode_flat_spec_field(flat_spec, "argument_set")
        self._post_spec_to_web_server("runcommand", unflatten_spec(flat_spec))

    def add_run_spec(self, run_spec: RunSpec) -> Sequence:
        flat_spec = flatten_spec(run_spec)
        flat_spec = json_encode_flat_spec_field(flat_spec, "info")
        flat_spec = json_encode_flat_spec_field(flat_spec, "data")
        if "artifact_tarball" not in flat_spec:
            flat_spec["artifact_tarball"] = None
        self._post_spec_to_web_server("run", flat_spec)

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

    def get_run(self, run_id: str) -> "Run":
        from pcs.run import Run

        return Run.from_registry(self, run_id)

    def _request_spec_from_web_server(
        self,
        spec_type: str,
        identifier: str,
        flatten: bool,
        error_if_not_found: bool = True,
    ) -> Optional[Dict]:
        assert spec_type in ["run", "runcommand", "repo", "component"]
        req_url = f"{self.root_api_url}/{spec_type}s/{identifier}/"
        response = requests.get(req_url)
        if not self._is_response_ok(response, error_if_not_found):
            return None
        flat_spec = json.loads(response.content)
        for spec_key, spec_val in [
            (k, v)
            for k, v in flat_spec.items()
            if k.endswith("_link") or v is None
        ]:
            logger.debug(
                f"Dropping field '{spec_key}: {spec_val}' from spec "
                "returned by web server."
            )
            flat_spec.pop(spec_key)
        return unflatten_spec(flat_spec) if not flatten else flat_spec

    def _post_spec_to_web_server(self, spec_type: str, spec: dict) -> None:
        """
        Handles HTTP request to backing webserver to upload a spec.
        Handles both nested and flat specs.
        """
        assert spec_type in ["run", "runcommand", "repo", "component"]
        req_url = f"{self.root_api_url}/{spec_type}s/"
        data = spec if is_flat(spec) else flatten_spec(spec)
        logger.debug(f"\nabout to post {spec_type} spec http request: {data}")
        response = requests.post(req_url, data=data)
        self._is_response_ok(response)
        result = json.loads(response.content)
        logger.debug(f"\npost {spec_type} spec http response:")
        logger.debug(pprint.pformat(result))

    def to_dict(self) -> Dict:
        raise Exception("to_dict() is not supported on WebRegistry.")
