import sys
import uuid
import logging
import importlib
from hashlib import sha1
from pathlib import Path
from dill.source import getsource as dill_getsource
from typing import Union, TypeVar, Dict, Type, Any, Sequence
from rich import print as rich_print
from rich.tree import Tree
from agentos.run_command import RunCommand
from agentos.component_run import ComponentRun
from agentos.identifiers import ComponentIdentifier
from agentos.specs import ComponentSpec, ComponentSpecKeys, unflatten_spec
from agentos.registry import (
    Registry,
    InMemoryRegistry,
)
from agentos.exceptions import RegistryException
from agentos.repo import RepoType, Repo, LocalRepo, GitHubRepo
from agentos.argument_set import ArgumentSet
from agentos.virtual_env import VirtualEnv
from agentos.utils import parse_github_web_ui_url

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about arguments, entry points, and
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
        requirements_path: str = None,
        instantiate: bool = True,
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
        :param requirements_path: Optional path to a pip installable file.
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
        self.requirements_path = requirements_path
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
    def from_github_registry(
        cls,
        github_url: str,
        name: str,
        version: str = None,
        use_venv: bool = True,
    ) -> "Component":
        """
        This method gets a Component from a registry file found on GitHub.  If
        the registry file contains a LocalRepo, this method automatically
        translates that LocalRepo into a GitHubRepo.  Pass ``use_venv=False``
        if you want to import and run the Component in your existing Python
        environment.

        The ``github_url`` argument can be found by navigating to the
        registry file on the GitHub web UI.  It should look like the
        following::

            https://github.com/<project>/<repo>/{blob,raw}/<branch>/<path>
        """
        project, repo, branch, repo_path = parse_github_web_ui_url(github_url)
        version = version or branch
        repo = Repo.from_github(project, repo)
        registry = Registry.from_repo(repo, repo_path, version)
        c_version = None
        if registry.has_component_by_name(name=name, version=version):
            c_version = version
        if use_venv:
            venv = VirtualEnv.from_registry(registry, name, c_version)
            venv.activate()
        return Component.from_registry(registry, name, c_version)

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
        if version:
            identifier = ComponentIdentifier(name, version)
        else:
            identifier = ComponentIdentifier.from_str(name)
        component_specs, repo_specs = registry.get_specs_transitively_by_id(
            identifier, flatten=True
        )
        repos = {
            repo_spec["identifier"]: Repo.from_spec(
                unflatten_spec(repo_spec), registry.base_dir
            )
            for repo_spec in repo_specs
        }
        components = {}
        dependencies = {}
        for component_spec in component_specs:
            component_id = ComponentIdentifier(
                component_spec["name"], component_spec["version"]
            )
            from_repo_args = {
                "repo": repos[component_spec["repo"]],
                "identifier": component_id,
                "class_name": component_spec["class_name"],
                "file_path": component_spec["file_path"],
            }
            if "requirements_path" in component_spec:
                from_repo_args["requirements_path"] = component_spec[
                    "requirements_path"
                ]
            if "instantiate" in component_spec.keys():
                from_repo_args["instantiate"] = component_spec["instantiate"]
            component = cls.from_repo(**from_repo_args)
            components[component_id] = component
            dependencies[component_id] = component_spec.get("dependencies", {})

        # Wire up the dependency graph
        for c_name, component in components.items():
            for attr_name, dependency_name in dependencies[c_name].items():
                dependency = components[dependency_name]
                component.add_dependency(dependency, attribute_name=attr_name)

        try:
            return components[identifier]
        except KeyError:
            # Try name without the version
            unversioned_components = {
                ComponentIdentifier.from_str(c_id.name): c_obj
                for c_id, c_obj in components.items()
            }
            return unversioned_components[identifier]

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
        identifier: str = None,
        repo: Repo = None,
        dunder_name: str = None,
        instantiate: bool = True,
    ) -> "Component":
        name = identifier if identifier else managed_cls.__name__
        if (
            managed_cls.__module__ == "__main__"
        ):  # handle classes defined in REPL.
            file_contents = dill_getsource(managed_cls)
            if repo:
                assert repo.type == RepoType.LOCAL, (
                    f"Repo '{repo.identifier}' is type {repo.type}, but must "
                    f"be {RepoType.LOCAL.value}."
                )
            else:
                repo = LocalRepo(identifier)
            sha = str(int(sha1(file_contents.encode("utf-8")).hexdigest(), 16))
            src_file = repo.get_local_repo_dir() / f"{name}-{sha}.py"
            if src_file.exists():
                print(f"Re-using existing source file {src_file}.")
            else:
                with open(src_file, "x") as f:
                    f.write(file_contents)
                print(f"Wrote new source file {src_file}.")
        else:
            managed_cls_module = sys.modules[managed_cls.__module__]
            assert hasattr(managed_cls_module, managed_cls.__name__), (
                "Components can only be created from classes that are "
                "available as an attribute of their module."
            )
            src_file = Path(managed_cls_module.__file__)
            logger.debug(
                f"Handling managed_cls {managed_cls.__name__} from existing "
                f"source file {src_file}. dir(managed_cls): \n"
            )
            repo = LocalRepo(f"{name}_repo", local_dir=src_file.parent)
            logger.debug(
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
        requirements_path: str = None,
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
            requirements_path=requirements_path,
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

    def run(self, entry_point: str, **kwargs):
        """
        Run an entry point with provided arguments. If you need to specify
        arguments to the init function of the managed object or any of
        its dependency components, use :py:func:run_with_arg_set:.

        :param entry_point: name of function to call on manage object.
        :param kwargs: keyword-only args to pass through to managed object
            function called entry-point.
        :return: the return value of the entry point called.
        """
        arg_set = ArgumentSet({self.name: {entry_point: kwargs}})
        run = self.run_with_arg_set(
            entry_point,
            args=arg_set,
            log_return_value=True,
        )
        return run.return_value

    def run_with_arg_set(
        self,
        entry_point: str,
        args: Union[ArgumentSet, Dict] = None,
        publish_to: Registry = None,
        log_return_value: bool = True,
        return_value_log_format: str = "yaml",
    ) -> ComponentRun:
        """
        Run the specified entry point a new instance of this Component's
        managed object given the specified args, log the results
        and return the Run object.

        :param entry_point: Name of a function to be called on a new
            instance of this component's managed object.
        :param args: A :py:func:agentos.argument_set.ArgumentSet: or
            ArgumentSet-like dict containing the entry-point arguments, and/or
            arguments to be passed to the __init__() functions of this
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
        if args:
            if not isinstance(args, ArgumentSet):
                args = ArgumentSet(args)
        else:
            args = ArgumentSet()
        run_command = RunCommand(self, entry_point, args)
        with ComponentRun.from_run_command(run_command) as run:
            for c in self.dependency_list():
                c.active_run = run
            # Note: get_object() adds the dunder component attribute before
            # calling __init__ on the instance.
            instance = self.get_object(arg_set=args)
            res = self.call_function_with_arg_set(instance, entry_point, args)
            if log_return_value:
                run.log_return_value(res, return_value_log_format)
            for c in self.dependency_list():
                c.active_run = None
            if publish_to:
                run.to_registry(publish_to)
            return run

    def call_function_with_arg_set(
        self, instance: Any, function_name: str, arg_set: ArgumentSet
    ) -> Any:
        fn = getattr(instance, function_name)
        assert fn is not None, f"{instance} has no attr {function_name}"
        fn_args = arg_set.get_function_args(self.name, function_name)
        print(f"Calling {self.name}.{function_name}(**{fn_args})")
        result = fn(**fn_args)
        return result

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

    def get_object(self, arg_set: ArgumentSet = None) -> T:
        collected = {}
        arg_set = arg_set if arg_set else ArgumentSet({})
        return self._get_object(arg_set, collected)

    def _get_object(self, arg_set: ArgumentSet, collected: dict) -> T:
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
                arg_set=arg_set, collected=collected
            )
            setattr(obj, dep_attr_name, dep_obj)
        setattr(obj, self._dunder_name, self)
        if self.instantiate:
            self._managed_cls.__init__ = save_init
            self.call_function_with_arg_set(obj, "__init__", arg_set)
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
        prefixed_reqs_path = None
        if self.requirements_path:
            prefixed_reqs_path = self.repo.get_prefixed_path_from_repo_root(
                new_identifier, self.requirements_path
            )
        clone = Component(
            managed_cls=self._managed_cls,
            repo=GitHubRepo(identifier=self.repo.identifier, url=repo_url),
            identifier=new_identifier,
            class_name=self.class_name,
            file_path=prefixed_file_path,
            requirements_path=prefixed_reqs_path,
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
        if self.requirements_path:
            component_spec_content["requirements_path"] = str(
                self.requirements_path
            )
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
                        add them. This includes dependencies on other
                        Components as well as dependencies a repo.
                        If they do, ensure that they are equal to
                        this component's dependencies (unless ``force`` is
                        specified).
        :param force: Optionally, if a component with the same identifier
                      already exists and is different than the current one,
                      attempt to overwrite the registered one with this one.
        """
        if not registry:
            registry = InMemoryRegistry()
        # Make sure this identifier does not exist in registry yet.
        existing_spec = registry.get_component_spec(
            self.identifier, error_if_not_found=False
        )
        if existing_spec and not force:
            if existing_spec != self.to_spec():
                raise RegistryException(
                    f"Component {self.identifier} already exists in registry "
                    f"{registry} and differs from the one you're trying to "
                    f"add. Specify force=True to overwrite it.\n"
                    f"existing: {existing_spec}"
                    "\nVS\n"
                    f"new: {self.to_spec()}"
                )
        # handle dependencies on other components
        if recurse:
            for c in self.dependency_list(include_root=False):
                existing_c_spec = registry.get_component_spec(
                    name=c.name,
                    version=c.version,
                    error_if_not_found=False,
                )
                if existing_c_spec and not force:
                    if existing_c_spec != c.to_spec():
                        raise RegistryException(
                            f"Trying to register a component {c.identifier} "
                            f"that already exists in a different form:\n"
                            f"{existing_c_spec}\n"
                            f"VS\n"
                            f"{c.to_spec()}\n\n"
                            f"To overwrite, specify force=true."
                        )
                # Either component dependency not in registry already or we are
                # force adding it.
                logger.debug(
                    f"recursively adding dependent component '{c.name}'"
                )
                c.to_registry(registry, recurse=recurse, force=force)

            # Either repo not in registry already or we are force adding it.
            self.repo.to_registry(registry, recurse=recurse, force=force)
        registry.add_component_spec(self.to_spec())
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
        ret_val = set()
        while component_queue:
            component = component_queue.pop()
            if include_root or component is not self:
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
