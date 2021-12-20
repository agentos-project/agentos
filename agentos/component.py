import sys
import uuid
import mlflow
import importlib
from typing import TypeVar, Dict, Type, Any, Sequence
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
from agentos.registry import Registry, InMemoryRegistry
from agentos.parameter_set import ParameterSet
from agentos.component_identifier import ComponentIdentifier
from agentos.specs import ComponentSpec

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about parameters, entry points, and
    dependencies.
    """

    Identifier = ComponentIdentifier

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
        identifier = Component.Identifier(name, version)
        component_identifiers = [identifier]
        repos = {}
        components = {}
        dependencies = {}
        while component_identifiers:
            component_id = component_identifiers.pop()
            component_spec = registry.get_component_spec_by_id(component_id)
            component_id_from_spec = ComponentIdentifier(
                component_spec["name"], component_spec["version"]
            )
            repo_id = component_spec["repo"]
            if repo_id not in repos.keys():
                repo_spec = registry.get_repo_spec(repo_id)
                repos[repo_id] = Repo.from_spec(
                    repo_id, repo_spec, registry.base_dir
                )
            component = Component.from_repo(
                repo=repos[repo_id],
                identifier=component_id_from_spec,
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
    def from_yaml(yaml_file: str, name: str, version: str = None):
        registry = Registry.from_yaml(yaml_file)
        return Component.from_registry(registry, name, version)

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
    ) -> None:
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if attribute_name is None:
            attribute_name = component.name
        self.dependencies[attribute_name] = component

    def get_instance(self, params: ParameterSet = None) -> None:
        instantiated = {}
        params = params if params else ParameterSet({})
        return self._get_instance(params, instantiated)

    def get_transitive_dependencies(
        self, include_root: bool = True
    ) -> Sequence["Component"]:
        """
        Return a normalized (i.e. flat) list containing all transitive
        dependencies of this component and (optionally) this component.

        :param include_root: Whether to include the root component in the list.
        :return: a list containing all all of the transitive dependencies
                 of this component (optionally  including the root component).
        """
        component_queue = [self]
        ret_val = set([self]) if include_root else set()
        while component_queue:
            component = component_queue.pop()
            ret_val.add(component)
            for dependency in component.dependencies.values():
                component_queue.append(dependency)
        return list(ret_val)

    def register(self, registry: Registry) -> None:
        """
        Registering a component adds a component spec for the component
        and each of it's transitive dependencies (which are themselves
        components) to the specified registry.
        """
        for c in self.get_transitive_dependencies():
            registry.add_component_spec(c.to_spec())
            try:
                repo_spec = registry.get_repo_spec(c.repo.name)
                err_msg = (
                    f"A Repo with identifier {c.repo.name} already exists"
                    f"in this registry that differs from the one referred to "
                    f"by component {c.identifier}."
                )
                assert repo_spec == c.repo.to_spec(), err_msg
            except LookupError:
                # Repo not yet registered, so so add it to this registry.
                registry.add_repo_spec(c.repo.to_spec())

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
        log_data_as_yaml_artifact("parameter_set.yaml", params.to_spec())

    def _log_component_spec(self) -> None:
        frozen = None
        try:
            frozen = self.to_frozen_registry().to_dict()
            log_data_as_yaml_artifact("agentos.yaml", frozen)
        except (BadGitStateException, NoLocalPathException) as exc:
            print(f"Warning: component is not publishable: {str(exc)}")
            spec = self.to_registry().to_dict()
            log_data_as_yaml_artifact("agentos.yaml", spec)
        mlflow.log_param("spec_is_frozen", frozen is not None)

    def _log_call(self, fn_name) -> None:
        mlflow.log_param("root_name", self.identifier.full)
        mlflow.log_param("entry_point", fn_name)

    def _handle_repo_spec(self, repos):
        existing_repo = repos.get(self.repo.name)
        if existing_repo:
            if self.repo.to_dict() != existing_repo:
                self.repo.name = str(uuid.uuid4())
        repos[self.repo.name] = self.repo.to_dict()

    def _get_versioned_dependency_dag(
        self, force: bool = False
    ) -> "Component":
        repo_url, version = self.repo.get_version_from_git(
            self.identifier, self.file_path, force
        )
        old_identifier = Component.Identifier(self.identifier.full)
        new_identifier = Component.Identifier(old_identifier.name, version)
        prefixed_file_path = self.repo.get_prefixed_path_from_repo_root(
            new_identifier, self.file_path
        )
        clone = Component(
            managed_cls=self._managed_cls,
            repo=GitHubRepo(name=self.repo.name, url=repo_url),
            identifier=new_identifier,
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

    def to_spec(self) -> ComponentSpec:
        dependencies = {
            k: str(v.identifier) for k, v in self.dependencies.items()
        }
        component_spec_content = {
            "repo": self.repo.name,
            "file_path": str(self.file_path),
            "class_name": self.class_name,
            "dependencies": dependencies,
        }
        return {str(self.identifier): component_spec_content}

    def to_registry(self) -> Registry:
        """
        Returns a registry containing this component and all of its
        transitive dependents, as well the repos of all of them.
        """
        registry = InMemoryRegistry()
        self.register(registry)
        return registry

    def to_frozen_registry(self, force: bool = False) -> Registry:
        versioned = self._get_versioned_dependency_dag(force)
        return versioned.to_registry()

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
