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
from agentos.repo import (
    Repo,
    InMemoryRepo,
    GitHubRepo,
    BadGitStateException,
    NoLocalPathException,
)
from agentos.parameter_set import ParameterSet

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class _Identifier:
    """
    This manages a Component Identifier so we can refer to Components both as
    [name] and [name]==[version] in agentos.yaml spec files or from the
    command-line.
    """

    def __init__(self, identifier: str, latest_refs=None):
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

    def __repr__(self) -> str:
        return f"<agentos.component.Component.Identifer: {self.full}>"

    @property
    def full(self) -> str:
        if self.name and self.version:
            return "==".join((self.name, self.version))
        return self.name


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about parameters, entry points, and
    dependencies.
    """

    Identifier = _Identifier

    def __init__(
        self,
        managed_cls: Type[T],
        repo: Repo,
        identifier: "Component.Identifier",
        class_name: str,
        file_path: str,
        dunder_name: str = None,
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
        self._dunder_name = dunder_name or "__component__"
        self._requirements = []
        self._dependencies = {}

    @staticmethod
    def from_yaml(
        name: str,
        component_spec_file: str,
    ) -> "Component":
        components = Component.parse_spec_file(component_spec_file)
        names = Component._get_name_map(component_spec_file)
        assert name in names, f'"{name}" not found in {names}'
        return components[names[name]]

    @staticmethod
    def from_class(
        managed_cls: Type[T],
        name: str = None,
        dunder_name: str = None,
    ) -> "Component":
        return Component(
            managed_cls=managed_cls,
            repo=InMemoryRepo(),
            identifier=Component.Identifier(managed_cls.__name__),
            class_name=managed_cls.__name__,
            file_path=".",
            dunder_name=dunder_name,
        )

    @staticmethod
    def from_repo(
        repo: Repo,
        identifier: "Component.Identifier",
        class_name: str,
        file_path: str,
        dunder_name: str = None,
    ) -> "Component":
        full_path = repo.get_local_file_path(identifier, file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        sys.path.append(str(full_path.parent))
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE_{class_name.upper()}", str(full_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        managed_cls = getattr(module, class_name)
        sys.path.pop()
        return Component(
            managed_cls=managed_cls,
            repo=repo,
            identifier=identifier,
            class_name=class_name,
            file_path=file_path,
            dunder_name=dunder_name,
        )

    @staticmethod
    def _get_name_map(component_spec_file: str) -> Dict:
        """
        User may refer to a component from, e.g., the CLI as a name without a
        version string (e.g. ``agent`` not ``agent==1.2.3``).  However, we want
        to map ``agent`` to ``agent==1.2.3`` if ``component_spec_file`` is
        pinned to a version.

        :returns: A dictionary that maps unversioned names to a full name that
        will uniquely identify a Component in this run context
        """
        with open(component_spec_file) as file_in:
            config = yaml.safe_load(file_in)
        components = config.get("components", {})
        names = {Component.Identifier(n).name: n for n in components.keys()}
        names.update({n: n for n in components.keys()})
        return names

    @staticmethod
    def parse_spec_file(spec_file: str) -> Dict:
        """Returns all Repos and Components defined by this ``spec_file``."""
        with open(spec_file) as file_in:
            config = yaml.safe_load(file_in)
        repos = Component._parse_repos(config.get("repos", {}))
        components = Component._parse_components(
            config.get("components", {}), repos
        )
        return components

    @staticmethod
    def _parse_repos(repos_spec: Dict) -> Dict:
        repos = {}
        for name, spec in repos_spec.items():
            repos[name] = Repo.from_spec(name, spec)
        return repos

    @staticmethod
    def _parse_components(components_spec: Dict, repos: Dict) -> Dict:
        components = {}
        dependency_names = {}
        for name, spec in components_spec.items():
            component = Component.from_repo(
                repo=repos[spec["repo"]],
                identifier=Component.Identifier(name),
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

    def get_default_entry_point(self):
        try:
            entry_point = self._managed_cls.DEFAULT_ENTRY_POINT
        except AttributeError:
            entry_point = "run"
        return entry_point

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
        frozen = None
        try:
            frozen = self.get_frozen_spec()
            log_data_as_yaml_artifact("agentos.yaml", frozen)
        except (BadGitStateException, NoLocalPathException) as exc:
            print(f"Warning: component is not publishable: {str(exc)}")
            spec = self.get_component_spec()
            log_data_as_yaml_artifact("agentos.yaml", spec)
        mlflow.log_param("spec_is_frozen", frozen is not None)

    def _log_call(self, fn_name) -> None:
        mlflow.log_param("root_name", self.identifier.full)
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

    def get_frozen_spec(self, force: bool = False) -> Dict:
        versioned = self._get_versioned_dependency_dag(force)
        return versioned.get_component_spec()

    def _get_versioned_dependency_dag(
        self, force: bool = False
    ) -> "Component":
        repo_url, version = self.repo.get_version_from_git(
            self.identifier, self.file_path, force
        )
        identifier = Component.Identifier(self.identifier.full)
        identifier.version = version
        prefixed_file_path = self.repo.get_prefixed_path_from_repo_root(
            identifier, self.file_path
        )
        clone = Component(
            managed_cls=self._managed_cls,
            repo=GitHubRepo(name=self.repo.name, url=repo_url),
            identifier=identifier,
            class_name=self.class_name,
            file_path=prefixed_file_path,
            dunder_name=self._dunder_name,
        )
        for attr_name, dependency in self._dependencies.items():
            frozen_dependency = dependency._get_versioned_dependency_dag(
                force=force
            )
            clone.add_dependency(frozen_dependency, attribute_name=attr_name)
        return clone

    def to_dict(self) -> Dict:
        dependencies = {k: v.full_name for k, v in self._dependencies.items()}
        component_spec = {
            "repo": self.repo.name,
            "file_path": str(self.file_path),
            "class_name": self.class_name,
            "dependencies": dependencies,
        }
        return component_spec

    def get_param_dict(self) -> Dict:
        param_dict = {}
        components = [self]
        while len(components) > 0:
            component = components.pop()
            param_dict[component.name] = copy.deepcopy(component._params)
            for dependency in component._dependencies.values():
                components.append(dependency)
        return param_dict

    @property
    def name(self) -> str:
        return self.identifier.name

    @property
    def full_name(self) -> str:
        return self.identifier.full

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
