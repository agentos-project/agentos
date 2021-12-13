import sys
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
from agentos.registry import Registry
from agentos.parameter_set import ParameterSet

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class _Identifier:
    """
    This manages a Component Identifier so we can refer to Components both as
    [name] and [name]==[version] in agentos.yaml spec files or from the
    command-line.
    """

    @staticmethod
    def from_str(identifier_string: str) -> "Component.identifier":
        split_identifier = str(identifier_string).split("==")
        assert (
            len(split_identifier) <= 2
        ), f"Bad identifier: '{identifier_string}'"
        if len(split_identifier) == 1:
            return _Identifier(split_identifier[0])
        else:
            print(f"returning {split_identifier[0]}, {split_identifier[1]}")
            return _Identifier(split_identifier[0], split_identifier[1])

    def __init__(
        self,
        name: str,
        version: str = None,
    ):
        assert "==" not in name, (
            f"Component.Identifier ({name} may not contain '=='. You should "
            f"probably use Component.Identifier.from_str() instead."
        )
        self._name = name
        self._version = version

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def full(self) -> str:
        if self._name and self._version:
            return "==".join((self._name, self._version))
        return self._name

    def __repr__(self) -> str:
        return f"<agentos.component.Component.Identifer: {self.full}>"

    def __hash__(self) -> int:
        return hash(self.full)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.full == other.full
        return self.full == other

    def __str__(self):
        return self.full


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
        dependencies: Dict = None,
        dunder_name: str = None,
    ):
        """
        :param managed_cls: The object this Component manages.
        :param repo: Where the code for this component's managed object is.
        :param identifier: Used to identify the Component.
        :param dependencies: List of other components that self depends on.
        :param dunder_name: Name used for the pointer to this Component on any
                            instances of ``managed_cls`` created by this
                            Component.
        """
        self._managed_cls = managed_cls
        self.repo = repo
        self.identifier = identifier
        self.class_name = class_name
        self.file_path = file_path
        self.dependencies = dependencies if dependencies else {}
        self._dunder_name = dunder_name or "__component__"
        self._requirements = []

    @staticmethod
    def from_registry(
        registry: Registry, name: str, version: str = None
    ) -> "Component":
        """
        Returns a Component Object from the provided registry, including
        its full dependency tree of other Component Objects.
        """
        components = registry.components(
            filter_by_name=name, filter_by_version=version
        )
        if len(components) == 0:
            raise LookupError(
                "This registry does not contain any components that match "
                "your filter criteria."
            )
        if len(components) > 1:
            raise LookupError(
                f"This registry contains more than one component with "
                f"the name {name}. Please specify a version."
            )
        identifier = Component.Identifier.from_str(list(components.keys())[0])
        print(f"Pushing {identifier} onto stack of components")
        component_identifiers = [identifier]
        repos = {}
        components = {}
        dependencies = {}
        while component_identifiers:
            component_id = component_identifiers.pop()
            component_spec = registry.component(component_id)
            repo_id = component_spec["repo"]
            if repo_id not in repos.keys():
                repo_spec = registry.repos[repo_id]
                repos[repo_id] = Repo.from_spec(
                    repo_id, repo_spec, registry.base_dir
                )
            component = Component.from_repo(
                repo=repos[repo_id],
                identifier=component_id,
                class_name=component_spec["class_name"],
                file_path=component_spec["file_path"],
            )
            components[component_id] = component
            dependencies[component_id] = component_spec.get("dependencies", {})
            for d_id in dependencies[component_id].values():
                component_identifiers.append(
                    Component.Identifier.from_str(d_id)
                )
                print(f"Pushing {d_id} onto stack of components")

        # Wire up the dependency graph
        for c_name, component in components.items():
            for attr_name, dependency_name in dependencies[c_name].items():
                dependency = components[dependency_name]
                component.add_dependency(dependency, attribute_name=attr_name)

        return components[identifier]

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

    @property
    def name(self) -> str:
        return self.identifier.name

    @property
    def full_name(self) -> str:
        return self.identifier.full

    @property
    def version(self):
        return self.identifier.version

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
        self.dependencies[attribute_name] = component

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
        for dep_attr_name, dep_component in self.dependencies.items():
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
            for dependency in component.dependencies.values():
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
        for attr_name, dependency in self.dependencies.items():
            frozen_dependency = dependency._get_versioned_dependency_dag(
                force=force
            )
            clone.add_dependency(frozen_dependency, attribute_name=attr_name)
        return clone

    def to_dict(self) -> Dict:
        dependencies = {k: v.full_name for k, v in self.dependencies.items()}
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
            for dependency in component.dependencies.values():
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
