import sys
import yaml
import copy
import uuid
import mlflow
import importlib
from typing import TypeVar, Dict, Type, Any
from contextlib import contextmanager
from agentos.utils import log_data_as_yaml_artifact
from agentos.utils import MLFLOW_EXPERIMENT_ID
from agentos.utils import get_version_from_git
from agentos.utils import get_prefixed_path_from_repo_root
from agentos.repo import RepoType, Repo, InMemoryRepo, GitHubRepo
from agentos.parameter_set import ParameterSet

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ComponentIdentifier:
    """
    This manages a Component Identifier so we can refer to Components both as
    [name] and [name]==[version] in agentos.yaml spec files or from the
    command-line.
    """

    def __init__(self, identifier, latest_refs=None):
        split_identifier = identifier.split("==")
        assert len(split_identifier) <= 2, f"Bad identifier: '{identifier}'"
        if len(split_identifier) == 1:
            self.name = split_identifier[0]
            if latest_refs:
                self.version = latest_refs[self.name]
            else:
                self.version = None
        else:
            self.name = split_identifier[0]
            self.version = split_identifier[1]

    @property
    def full(self):
        if self.name and self.version:
            return "==".join((self.name, self.version))
        return self.name


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about parameters, entry points, and
    dependencies.
    """

    def __init__(
        self,
        managed_cls: Type[T],
        repo: Repo,
        identifier: ComponentIdentifier,
        class_name: str,
        file_path: str,
        dunder_name: str = "__component__",
    ):
        """
        :param managed_cls: The class used to create instances.
        :param name: Name used to identify the Component.
        :param dunder_name: Name used for the pointer to this Component on any
                            instances of ``managed_cls`` created by this
                            Component.
        """
        self._managed_cls = managed_cls
        self.repo = repo
        self.identifier = identifier
        self.class_name = class_name
        self.file_path = file_path
        self._dunder_name = dunder_name
        self._requirements = []
        self._dependencies = {}

    @classmethod
    def get_from_yaml(
        cls,
        name: str,
        component_spec_file: str,
    ) -> "Component":
        components = cls.parse_spec_file(component_spec_file)
        # User may run without version string (e.g. "agent" not "agent==1.2.3")
        names = {ComponentIdentifier(n).name: n for n in components.keys()}
        names.update({n: n for n in components.keys()})
        assert name in names, f'"{name}" not found in {names}'
        return components[names[name]]

    @classmethod
    def get_from_class(
        cls,
        managed_cls: Type[T],
        name: str = None,
        dunder_name: str = "__component__",
    ) -> "Component":
        return Component(
            managed_cls=managed_cls,
            repo=InMemoryRepo(),
            identifier=ComponentIdentifier(managed_cls.__name__),
            class_name=managed_cls.__name__,
            file_path=".",
            dunder_name=dunder_name,
        )

    @classmethod
    def get_from_repo(
        cls,
        repo: Repo,
        identifier: ComponentIdentifier,
        class_name: str,
        file_path: str,
        dunder_name: str = "__component__",
    ) -> "Component":
        full_path = get_full_path(repo, identifier, file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        sys.path.append(str(full_path.parent))
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE_{class_name.upper()}", str(full_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, class_name)
        sys.path.pop()
        return Component(
            managed_cls=cls,
            repo=repo,
            identifier=identifier,
            class_name=class_name,
            file_path=file_path,
            dunder_name=dunder_name,
        )

    @classmethod
    def parse_spec_file(cls, spec_file: str) -> Dict:
        """Returns all Repos and Components defined by this ``spec_file``."""
        with open(spec_file) as file_in:
            config = yaml.safe_load(file_in)
        repos = cls._parse_repos(config.get("repos", {}))
        components = cls._parse_components(config.get("components", {}), repos)
        return components

    @classmethod
    def _parse_repos(cls, repos_spec: Dict) -> Dict:
        repos = {}
        for name, spec in repos_spec.items():
            repos[name] = Repo.from_spec(name, spec)
        return repos

    @classmethod
    def _parse_components(cls, components_spec: Dict, repos: Dict) -> Dict:
        components = {}
        dependency_names = {}
        for name, spec in components_spec.items():
            component = Component.get_from_repo(
                repo=repos[spec["repo"]],
                identifier=ComponentIdentifier(name),
                class_name=spec["class_name"],
                file_path=spec["file_path"],
            )
            components[name] = component
            dependency_names[name] = spec.get("dependencies", {})

        # Wire up the dependency graph
        for name, component in components.items():
            for attr_name, dependency_name in dependency_names[name].items():
                dependency = components[dependency_name]
                component.add_dependency(dependency, attribute_name=attr_name)

        return components

    def get_full_path(self):
        return get_full_path(self.repo, self.identifier, self.file_path)

    def run(
        self,
        fn_name: str,
        params: ParameterSet = None,
        tracked: bool = True,
        instance: Any = None,
    ):
        params = params if params else ParameterSet()
        manager = self._track_run if tracked else self._no_track_run
        with manager(fn_name, params):
            instance = (
                instance if instance else self.get_instance(params=params)
            )
            fn = getattr(instance, fn_name)
            assert fn is not None, f"{instance} has no attr {fn_name}"
            fn_params = params.get(self.name, fn_name)
            print(f"Calling {self.name}.{fn_name}(**{fn_params})")
            result = fn(**fn_params)
            return result

    def add_dependency(
        self, component: "Component", attribute_name: str = None
    ):
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if attribute_name is None:
            attribute_name = component.name
        self._dependencies[attribute_name] = component

    def get_instance(self, params: ParameterSet = None) -> None:
        instantiated = {}
        params = params if params else ParameterSet({})
        return self._get_instance(params, instantiated)

    def _get_instance(self, params: ParameterSet, instantiated: dict) -> T:
        if self.name in instantiated:
            return instantiated[self.name]
        save_init = self._managed_cls.__init__
        self._managed_cls.__init__ = lambda self: None
        instance = self._managed_cls()
        for dep_attr_name, dep_component in self._dependencies.items():
            print(f"Adding {dep_attr_name} to {self.name}")
            dep_instance = dep_component._get_instance(
                params=params, instantiated=instantiated
            )
            setattr(instance, dep_attr_name, dep_instance)
        setattr(instance, self._dunder_name, self)
        self._managed_cls.__init__ = save_init
        self.run("__init__", params=params, instance=instance, tracked=False)
        instantiated[self.name] = instance
        return instance

    def _log_params(self, params: ParameterSet) -> None:
        log_data_as_yaml_artifact("parameter_set.yaml", params.to_dict())

    def _log_component_spec(self) -> None:
        spec = self.get_component_spec()
        log_data_as_yaml_artifact("agentos.yaml", spec)
        is_published = True
        for repo_name, repo_data in spec["repos"].items():
            is_published &= repo_data["type"] == RepoType.GITHUB.value
        mlflow.log_param("is_published", is_published)

    def _log_call(self, fn_name) -> None:
        mlflow.log_param("entry_point", fn_name)

    def get_component_spec(self):
        spec = {"repos": {}, "components": {}}
        components = [self]
        while len(components) > 0:
            component = components.pop()
            component._handle_repo_spec(spec["repos"])
            spec["components"][component.full_name] = component.to_dict()
            for dependency in component._dependencies.values():
                components.append(dependency)
        return spec

    def _handle_repo_spec(self, repos):
        existing_repo = repos.get(self.repo.name)
        if existing_repo:
            if self.repo.to_dict() != existing_repo:
                self.repo.name = str(uuid.uuid4())
        repos[self.repo.name] = self.repo.to_dict()

    def get_pinned_component_spec(self):
        versioned = self._get_versioned_component_dag()
        return versioned.get_component_spec()

    def _get_versioned_component_dag(self):
        full_path = self.get_full_path()
        repo_url, version = get_version_from_git(full_path)
        identifier = ComponentIdentifier(self.identifier.full)
        identifier.version = version
        clone = Component(
            managed_cls=self._managed_cls,
            repo=GitHubRepo(name=self.repo.name, url=repo_url),
            identifier=identifier,
            class_name=self.class_name,
            file_path=get_prefixed_path_from_repo_root(full_path),
            dunder_name=self._dunder_name,
        )
        for alias, dependency in self._dependencies.items():
            pinned_dependency = dependency._get_versioned_component_dag()
            clone.add_dependency(pinned_dependency, alias=alias)
        return clone

    @property
    def name(self):
        return self.identifier.name

    @property
    def full_name(self):
        return self.identifier.full

    def to_dict(self):
        dependencies = {k: v.full_name for k, v in self._dependencies.items()}
        return {
            "repo": self.repo.name,
            "file_path": str(self.file_path),
            "class_name": self.class_name,
            "dependencies": dependencies,
        }

    def get_param_dict(self) -> Dict:
        param_dict = {}
        components = [self]
        while len(components) > 0:
            component = components.pop()
            param_dict[component.name] = copy.deepcopy(component._params)
            for dependency in component._dependencies.values():
                components.append(dependency)
        return param_dict

    @contextmanager
    def _track_run(self, fn_name: str, params: ParameterSet):
        mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
        self._log_params(params)
        self._log_component_spec()
        self._log_call(fn_name)
        try:
            yield
        finally:
            mlflow.end_run()

    @contextmanager
    def _no_track_run(self, fn_name: str, params: ParameterSet):
        try:
            yield
        finally:
            pass


def get_full_path(repo: Repo, identifier: ComponentIdentifier, file_path: str):
    return (repo.get_file_path(identifier.version) / file_path).absolute()
