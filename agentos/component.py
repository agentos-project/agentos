import sys
import uuid
import importlib
from pathlib import Path
from dill.source import getsource as dill_getsource
from typing import Union, TypeVar, Dict, Type, Any, Sequence, Optional
from rich import print as rich_print
from rich.tree import Tree
from agentos.run import Run
from agentos.run_command import RunCommand
from agentos.component_run import ComponentRun
from agentos.identifiers import ComponentIdentifier
from agentos.specs import ComponentSpec, ComponentSpecKeys
from agentos.registry import (
    Registry,
    InMemoryRegistry,
)
from agentos.exceptions import RegistryException
from agentos.repo import Repo, LocalRepo, GitHubRepo
from agentos.parameter_set import ParameterSet

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
        instantiate: Optional[bool] = True,
        dependencies: Dict = None,
        dunder_name: str = None,
    ):
        """
        :param managed_cls: The object this Component manages.
        :param repo: Where the code for this component's managed object is.
        :param identifier: Used to identify the Component.
        :param class_name: The name of the class that is being managed.
        :param file_path: The python module file where the managed class is
            defined.
        :param instantiate: Optional. If True, then get_object() return an
            instance of the managed class; if False, it returns a class object.
        :param dependencies: List of other components that self depends on.
        :param dunder_name: Name used for the pointer to this Component on any
            instances of ``managed_cls`` created by this Component.
        """
        self._managed_cls = managed_cls
        self.repo = repo
        self.identifier = identifier
        self.class_name = class_name
        self.file_path = file_path
        if not class_name:
            assert (
                not instantiate
            ), "instantiate can only be True if a class_name is provided"
        self.instantiate = instantiate
        self.dependencies = dependencies if dependencies else {}
        self._dunder_name = dunder_name or "__component__"
        self._requirements = []
        self.active_run = None

    @classmethod
    def from_default_registry(
        cls, name: str, version: str = None
    ) -> "Component":
        return cls.from_registry(Registry.from_default(), name, version)

    @classmethod
    def from_registry(
        cls, registry: Registry, name: str, version: str = None
    ) -> "Component":
        """
        Returns a Component Object from the provided registry, including
        its full dependency tree of other Component Objects.
        If no Registry is provided, use the default registry.
        """
        identifier = Component.Identifier(name, version)
        component_identifiers = [identifier]
        repos = {}
        components = {}
        dependencies = {}
        while component_identifiers:
            component_id = component_identifiers.pop()
            component_spec = registry.get_component_spec_by_id(
                component_id, flatten=True
            )
            component_id_from_spec = ComponentIdentifier(
                component_spec["name"], component_spec["version"]
            )
            repo_id = component_spec["repo"]
            if repo_id not in repos.keys():
                repo_spec = registry.get_repo_spec(repo_id)
                repos[repo_id] = Repo.from_spec(repo_spec, registry.base_dir)
            from_repo_args = {
                "repo": repos[repo_id],
                "identifier": component_id_from_spec,
                "class_name": component_spec["class_name"],
                "file_path": component_spec["file_path"],
            }
            if "instantiate" in component_spec.keys():
                from_repo_args["instantiate"] = component_spec["instantiate"]
            component = cls.from_repo(**from_repo_args)
            components[component_id] = component
            dependencies[component_id] = component_spec.get("dependencies", {})
            for d_id in dependencies[component_id].values():
                component_identifiers.append(
                    Component.Identifier.from_str(d_id)
                )

        # Wire up the dependency graph
        for c_name, component in components.items():
            for attr_name, dependency_name in dependencies[c_name].items():
                dependency = components[dependency_name]
                component.add_dependency(dependency, attribute_name=attr_name)

        return components[identifier]

    @classmethod
    def from_registry_file(
        cls, yaml_file: str, name: str, version: str = None
    ) -> "Component":
        registry = Registry.from_yaml(yaml_file)
        return cls.from_registry(registry, name, version)

    @classmethod
    def from_class(
        cls,
        managed_cls: Type[T],
        name: str = None,
        dunder_name: str = None,
        instantiate: bool = True,
    ) -> "Component":
        name = name if name else managed_cls.__name__
        if (
            managed_cls.__module__ == "__main__"
        ):  # handle classes defined in REPL.
            repo = LocalRepo(name)
            src_file = repo.get_local_repo_dir() / f"{name}.py"
            with open(src_file, "w") as f:
                f.write(dill_getsource(managed_cls))
            print(f"Wrote new source file {src_file}.")
        else:
            managed_cls_module = sys.modules[managed_cls.__module__]
            assert hasattr(managed_cls_module, managed_cls.__name__), (
                "Components can only be created from classes that are "
                "available as an attribute of their module."
            )
            src_file = Path(managed_cls_module.__file__)
            print(
                f"handling managed_cls {managed_cls.__name__} from existing "
                f"source file {src_file}. dir(managed_cls): \n"
            )
            repo = LocalRepo(f"{name}_repo", local_dir=src_file.parent)
            print(
                f"Created LocalRepo {repo.identifier} from existing source "
                f"file {src_file}."
            )
        return cls(
            managed_cls=managed_cls,
            repo=repo,
            identifier=Component.Identifier(name),
            class_name=managed_cls.__name__,
            file_path=src_file.name,
            instantiate=instantiate,
            dunder_name=dunder_name,
        )

    @classmethod
    def from_repo(
        cls,
        repo: Repo,
        identifier: Union[str, "Component.Identifier"],
        class_name: str,
        file_path: str,
        instantiate: bool = True,
        dunder_name: str = None,
    ) -> "Component":
        # For convenience, optionally allow 'identifier' to be passed as str.
        identifier = ComponentIdentifier.from_str(str(identifier))
        full_path = repo.get_local_file_path(identifier.version, file_path)
        assert full_path.is_file(), f"{full_path} does not exist"
        sys.path.append(str(full_path.parent))
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE_{class_name.upper()}", str(full_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        managed_cls = getattr(module, class_name)
        sys.path.pop()
        return cls(
            managed_cls=managed_cls,
            repo=repo,
            identifier=identifier,
            class_name=class_name,
            file_path=file_path,
            instantiate=instantiate,
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
        entry_point: str,
        params: Union[ParameterSet, Dict] = None,
        publish_to: Registry = None,
        log_return_value: bool = True,
        return_value_log_format: str = "pickle",
    ) -> Run:
        """
        Run the specified entry point a new instance of this components
        managed object given the specified params, log the results
        and return the Run object.

        :param entry_point: Name of a function to be called on a new
            instance of this component's managed object.
        :param params: A :py:func:agentos.parameter_set.ParameterSet: or
            ParameterSet-like dict containing the entry-point parameters and/or
            parameters to be passed to the __init__() functions of this
            component's dependents during managed object initialization.
        :param publish_to: Optionally, publish the resulting Run object
            to the provided registry.
        :param log_return_value: If True, log the return value of the entry
            point being run.
        :param return_value_log_format: Specify which format to use when
            serializing the return value. Only used if ``log_return_value``
            is True.
        """
        assert not self.active_run, (
            f"Component {self.identifier} already has an active_run, so a "
            "new run is not allowed."
        )
        if params:
            if not isinstance(params, ParameterSet):
                params = ParameterSet(params)
        else:
            params = ParameterSet()
        run_command = RunCommand(self, entry_point, params)
        with ComponentRun.from_run_command(run_command) as run:
            for c in self.dependency_list():
                c.active_run = run
            # Note: get_object() adds the dunder component attribute before
            # calling __init__ on the instance.
            instance = self.get_object(params=params)
            res = self.call_function_with_param_set(
                instance, entry_point, params
            )
            if log_return_value:
                run.log_return_value(res, return_value_log_format)
            for c in self.dependency_list():
                c.active_run = None
            if publish_to:
                run.to_registry(publish_to)
            return run

    def call_function_with_param_set(
        self, instance: Any, function_name: str, param_set: ParameterSet
    ) -> Any:
        fn = getattr(instance, function_name)
        assert fn is not None, f"{instance} has no attr {function_name}"
        fn_params = param_set.get_function_params(self.name, function_name)
        print(f"Calling {self.name}.{function_name}(**{fn_params})")
        return fn(**fn_params)

    def add_dependency(
        self, component: "Component", attribute_name: str = None
    ) -> None:
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if attribute_name is None:
            attribute_name = component.name
        assert attribute_name not in self.dependencies, (
            f"{self.identifier} already has a dependency with attribute "
            f"{attribute_name}. Please use a different attribute name."
        )
        self.dependencies[attribute_name] = component

    def get_object(self, params: ParameterSet = None) -> T:
        collected = {}
        params = params if params else ParameterSet({})
        return self._get_object(params, collected)

    def _get_object(self, params: ParameterSet, collected: dict) -> T:
        if self.name in collected:
            return collected[self.name]
        if self.instantiate:
            save_init = self._managed_cls.__init__
            self._managed_cls.__init__ = lambda self: None
            obj = self._managed_cls()
        else:
            print(f"getting {self._managed_cls} w/o instantiating ")
            obj = self._managed_cls
        for dep_attr_name, dep_component in self.dependencies.items():
            print(f"Adding {dep_attr_name} to {self.name}")
            dep_obj = dep_component._get_object(
                params=params, collected=collected
            )
            setattr(obj, dep_attr_name, dep_obj)
        setattr(obj, self._dunder_name, self)
        if self.instantiate:
            self._managed_cls.__init__ = save_init
            self.call_function_with_param_set(obj, "__init__", params)
        collected[self.name] = obj
        return obj

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
            repo=GitHubRepo(identifier=self.repo.identifier, url=repo_url),
            identifier=new_identifier,
            class_name=self.class_name,
            file_path=prefixed_file_path,
            instantiate=self.instantiate,
            dunder_name=self._dunder_name,
        )
        for attr_name, dependency in self.dependencies.items():
            frozen_dependency = dependency._get_versioned_dependency_dag(
                force=force
            )
            clone.add_dependency(frozen_dependency, attribute_name=attr_name)
        return clone

    def to_spec(self, flatten: bool = False) -> ComponentSpec:
        dependencies = {
            k: str(v.identifier) for k, v in self.dependencies.items()
        }
        component_spec_content = {
            "repo": self.repo.identifier,
            "file_path": str(self.file_path),
            "class_name": self.class_name,
            "dependencies": dependencies,
        }
        if flatten:
            component_spec_content.update(
                {ComponentSpecKeys.IDENTIFIER: str(self.identifier)}
            )
            return component_spec_content
        else:
            return {str(self.identifier): component_spec_content}

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        force: bool = False,
    ) -> Registry:
        """
        Returns a registry containing specs for this component, all of its
        transitive dependents, and the repos of all of them. Throws an
        exception if any of them already exist in the Registry that are
        different unless ``force`` is set to True.

        :param registry: Optionally, add the component spec for this component
                         and each of its transitive dependencies (which are
                         themselves components) to the specified registry.
        :param recurse: If True, check that all transitive dependencies
                        exist in the registry already, and if they don't, then
                        add them. If they do, ensure that they are equal to
                        this component's dependencies (unless ``force`` is
                        specified).
        :param force: Optionally, if a component with the same identifier
                      already exists and is different than the current one,
                      attempt to overwrite the registered one with this one.
        """
        if not registry:
            registry = InMemoryRegistry()
        for c in self.dependency_list():
            existing_c_spec = registry.get_component_specs(
                filter_by_name=c.name, filter_by_version=c.version
            )
            if existing_c_spec and not force:
                if existing_c_spec != c.to_spec():
                    raise RegistryException(
                        f"Trying to register a component {c.identifier} that "
                        f"already exists in a different form:\n"
                        f"{existing_c_spec}\n"
                        f"VS\n"
                        f"{c.to_spec()}\n\n"
                        f"To overwrite, specify force=true."
                    )
            registry.add_component_spec(c.to_spec())
            try:
                repo_spec = registry.get_repo_spec(c.repo.identifier)
                if repo_spec != c.repo.to_spec():
                    raise RegistryException(
                        f"A Repo with identifier {c.repo.identifier} already "
                        "exists in this registry that differs from the one "
                        f"referred to by component {c.identifier}.\n"
                        f"New repo spec:\n{repo_spec}\n\n"
                        f"Existing repo spec:\n{c.repo.to_spec()}"
                    )
            except LookupError:
                # Repo not yet registered, so so add it to this registry.
                registry.add_repo_spec(c.repo.to_spec())
            if not recurse:
                break
        return registry

    def to_frozen_registry(self, force: bool = False) -> Registry:
        versioned = self._get_versioned_dependency_dag(force)
        return versioned.to_registry()

    def dependency_list(
        self, include_root: bool = True
    ) -> Sequence["Component"]:
        """
        Return a normalized (i.e. flat) Sequence containing all transitive
        dependencies of this component and (optionally) this component.

        :param include_root: Whether to include root component in the list.
                             If True, self is first element in list returned.
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

    def print_status_tree(self) -> None:
        tree = self.get_status_tree()
        rich_print(tree)

    def get_status_tree(self, parent_tree: Tree = None) -> Tree:
        self_tree = Tree(f"Component: {self.identifier.full}")
        if parent_tree is not None:
            parent_tree.add(self_tree)
        for dep_attr_name, dep_component in self.dependencies.items():
            dep_component.get_status_tree(parent_tree=self_tree)
        return self_tree
