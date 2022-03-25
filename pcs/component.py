import importlib
import logging
import sys
import uuid
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Sequence, Type, TypeVar, Union

from dill.source import getsource as dill_getsource
from rich import print as rich_print
from rich.tree import Tree

from pcs.argument_set import ArgumentSet
from pcs.component_run import ComponentRun
from pcs.exceptions import RegistryException
from pcs.identifiers import ComponentIdentifier
from pcs.registry import InMemoryRegistry, Registry
from pcs.repo import GitHubRepo, LocalRepo, Repo, RepoType
from pcs.run_command import RunCommand
from pcs.specs import ComponentSpec, ComponentSpecKeys, unflatten_spec
from pcs.utils import parse_github_web_ui_url
from pcs.virtual_env import NoOpVirtualEnv, VirtualEnv

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Component:
    """
    A Component is an object manager. Objects can be Python Modules, Python
    Classes, or Python Class Instances. The Component abstraction provides a
    standard programmatic mechanism for managing dependencies between these
    objects, reproducibly creating/initializing them and executing their
    methods. You can think of methods on a managed object as "managed methods"
    which we call "Entry Points". We call the execution of an Entry Point a
    "Run". Components provide reproducibility by automatically tracking (i.e.,
    logging) all of the parts that make up a Run, including: (1) the code of
    the object being run (i.e., the Component and its Entry Point), (2) the
    full DAG of other objects it depends on (i.e., DAG of other Components),
    (3) the set of arguments (literally an ``ArgumentSet``) used during
    initialization of the managed object and all objects it transitively
    depends on, and (4) the arguments passed to the Entry Point being run.
    """

    def __init__(
        self,
        repo: Repo,
        identifier: ComponentIdentifier,
        file_path: str,
        class_name: str = None,
        instantiate: bool = False,
        requirements_path: str = None,
        dependencies: Dict = None,
        use_venv: bool = True,
        dunder_name: str = None,
    ):
        """
        :param repo: Repo where this component's module file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param identifier: Used to identify the Component.
        :param file_path: Path to Python module file this Component manages.
        :param class_name: Optionally, the name of the class that is being
            managed. If none provided, then by default this component is a
            managed Python Module.
        :param instantiate: Optional. If True, this Component is a managed
            Python Class Instance, ``class_name`` must also be passed, and
            ``get_object()`` returns an instance of the class with name
            ``class_name``. If False and ``class_name`` is provided, then
            this Component is a managed Python Class and ``get_object()``
            returns a Python Class object specified by ``class_name``.
            If False and ``class_name`` is not provided, this Component is
            a managed Python Module and ``get_object()`` returns a
            Python Module object.
        :param requirements_path: Optional path to a pip installable file.
        :param dependencies: List of other components that self depends on.
        :param use_venv: Whether to create a VM when setting up the object
            this component manages.
        :param dunder_name: Name used for the pointer to this Component on any
            managed objects created by this Component.
        """
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
        self._use_venv = use_venv
        self._venv = None
        self._dunder_name = dunder_name or "__component__"
        self._requirements = []
        self._parent_components = set()
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
        project, repo, branch, reg_file_path = parse_github_web_ui_url(
            github_url
        )
        version = version or branch
        repo = Repo.from_github(project, repo)
        registry = Registry.from_file_in_repo(repo, reg_file_path, version)
        c_version = None
        if registry.has_component_by_name(name=name, version=version):
            c_version = version
        component = cls.from_registry(
            registry, name, c_version, use_venv=use_venv
        )
        return component

    @classmethod
    def from_default_registry(
        cls, name: str, version: str = None, use_venv: bool = True
    ) -> "Component":
        return cls.from_registry(
            Registry.from_default(), name, version, use_venv=use_venv
        )

    @classmethod
    def from_registry(
        cls,
        registry: Registry,
        name: str,
        version: str = None,
        use_venv: bool = True,
    ) -> "Component":
        """
        Returns a Component Object from the provided registry, including
        its full dependency tree of other Component Objects.
        If no Registry is provided, use the default registry.
        """
        if version:
            identifier = ComponentIdentifier(name, version)
        else:
            identifier = ComponentIdentifier(name)
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
                "file_path": component_spec["file_path"],
                "use_venv": use_venv,
            }
            if "class_name" in component_spec:
                from_repo_args["class_name"] = component_spec["class_name"]
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
                ComponentIdentifier(c_id.name): c_obj
                for c_id, c_obj in components.items()
            }
            return unversioned_components[identifier]

    @classmethod
    def from_registry_file(
        cls,
        yaml_file: str,
        name: str,
        version: str = None,
        use_venv: bool = True,
    ) -> "Component":
        registry = Registry.from_yaml(yaml_file)
        return cls.from_registry(registry, name, version, use_venv=use_venv)

    @classmethod
    def from_class(
        cls,
        class_obj: Type[T],
        repo: Repo = None,
        identifier: str = None,
        instantiate: bool = False,
        use_venv: bool = True,
        dunder_name: str = None,
    ) -> "Component":
        name = identifier if identifier else class_obj.__name__
        if (
            class_obj.__module__ == "__main__"
        ):  # handle classes defined in REPL.
            file_contents = dill_getsource(class_obj)
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
            managed_obj_module = sys.modules[class_obj.__module__]
            assert hasattr(managed_obj_module, class_obj.__name__), (
                "Components can only be created from classes that are "
                "available as an attribute of their module."
            )
            src_file = Path(managed_obj_module.__file__)
            logger.debug(
                f"Handling class_obj {class_obj.__name__} from existing "
                f"source file {src_file}."
            )
            repo = LocalRepo(f"{name}_repo", local_dir=src_file.parent)
            logger.debug(
                f"Created LocalRepo {repo.identifier} from existing source "
                f"file {src_file}."
            )
        return cls(
            repo=repo,
            identifier=ComponentIdentifier(name),
            file_path=src_file.name,
            class_name=class_obj.__name__,
            instantiate=instantiate,
            use_venv=use_venv,
            dunder_name=dunder_name,
        )

    @classmethod
    def from_repo(
        cls,
        repo: Repo,
        identifier: str,
        file_path: str,
        class_name: str = None,
        instantiate: bool = False,
        requirements_path: str = None,
        use_venv: bool = True,
        dunder_name: str = None,
    ) -> "Component":
        # For convenience, optionally allow 'identifier' to be passed as str.
        identifier = ComponentIdentifier(identifier)
        full_path = repo.get_local_file_path(file_path, identifier.version)
        assert full_path.is_file(), f"{full_path} does not exist"
        return cls(
            repo=repo,
            identifier=identifier,
            class_name=class_name,
            file_path=file_path,
            requirements_path=requirements_path,
            instantiate=instantiate,
            use_venv=use_venv,
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
            imported_obj = self._import_object()
            entry_point = imported_obj.DEFAULT_ENTRY_POINT
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
        run_command = RunCommand(self, entry_point, args, log_return_value)
        with ComponentRun.from_run_command(run_command) as run:
            for c in self.dependency_list():
                c.active_run = run
            # Note: get_object() adds the dunder component attribute before
            # calling __init__ on the instance.
            obj = self.get_object(arg_set=args)
            res = self.call_function_with_arg_set(obj, entry_point, args)
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
        if self._venv and component.requirements_path:
            raise Exception(
                "You cannot add a dependency with a requirements_path after a "
                "virtual env has already been constructed and activated. Try "
                "restarting Python and rebuilding your dependency graph"
            )
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if attribute_name is None:
            attribute_name = component.name
        assert attribute_name not in self.dependencies, (
            f"{self.identifier} already has a dependency with attribute "
            f"{attribute_name}. Please use a different attribute name."
        )
        self.dependencies[attribute_name] = component
        component._parent_components.add(self)

    def get_object(self, arg_set: ArgumentSet = None) -> T:
        collected = {}
        arg_set = arg_set if arg_set else ArgumentSet({})
        return self._get_object(arg_set, collected)

    def _get_object(self, arg_set: ArgumentSet, collected: dict) -> T:
        if self.name in collected:
            return collected[self.name]
        imported_obj = self._import_object()
        if self.instantiate:
            save_init = imported_obj.__init__
            imported_obj.__init__ = lambda self: None
            obj = imported_obj()
        else:
            print(f"getting {imported_obj} w/o instantiating ")
            obj = imported_obj
        for dep_attr_name, dep_component in self.dependencies.items():
            print(f"Adding {dep_attr_name} to {self.name}")
            dep_obj = dep_component._get_object(
                arg_set=arg_set, collected=collected
            )
            setattr(obj, dep_attr_name, dep_obj)
        setattr(obj, self._dunder_name, self)
        if self.instantiate:
            imported_obj.__init__ = save_init
            self.call_function_with_arg_set(obj, "__init__", arg_set)
        collected[self.name] = obj
        return obj

    def _import_object(self):
        """Return managed module, or class if ``self.class_name`` is set."""
        if not self._venv:
            self._venv = self._build_virtual_env()
            self._venv.activate()
        full_path = self.repo.get_local_file_path(
            self.file_path, self.identifier.version
        )
        assert full_path.is_file(), f"{full_path} does not exist"
        suffix = f"_{self.class_name.upper()}" if self.class_name else ""
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE{suffix}", str(full_path)
        )
        managed_obj = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(full_path.parent))
        spec.loader.exec_module(managed_obj)
        if self.class_name:
            managed_obj = getattr(managed_obj, self.class_name)
        return managed_obj

    def _build_virtual_env(self) -> VirtualEnv:
        # Only the root Component will setup and activate the VirtualEnv
        if not self._use_venv or self._parent_components:
            return NoOpVirtualEnv()
        req_paths = set()
        for c in self.dependency_list(include_parents=True):
            if c.requirements_path is None:
                continue
            for req_path in c.requirements_path.split(";"):
                full_req_path = self.repo.get_local_file_path(
                    req_path, c.identifier.version
                ).absolute()
                req_paths.add(full_req_path)
        return VirtualEnv.from_requirements_paths(req_paths)

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
        old_identifier = ComponentIdentifier(self.identifier)
        new_identifier = ComponentIdentifier(old_identifier.name, version)
        prefixed_file_path = self.repo.get_prefixed_path_from_repo_root(
            new_identifier, self.file_path
        )
        prefixed_reqs_path = None
        if self.requirements_path:
            prefixed_reqs_path = self.repo.get_prefixed_path_from_repo_root(
                new_identifier, self.requirements_path
            )
        clone = Component(
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
            "dependencies": dependencies,
            "class_name": self.class_name,
            "instantiate": self.instantiate,
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
        self, include_root: bool = True, include_parents: bool = False
    ) -> Sequence["Component"]:
        """
        Return a normalized (i.e. flat) Sequence containing all transitive
        dependencies of this component and (optionally) this component.

        :param include_root: Whether to include root component in the list.
                             If True, self is included in the list returned.
        :param include_parents: If True, then recursively include all parents
                                of this component (and their parents, etc).
                                A parent of this Component is a Component
                                which depends on this Component.  Ultimately,
                                if True, all Components in the DAG will be
                                returned.

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
                if dependency not in ret_val:
                    component_queue.append(dependency)
            if include_parents:
                for parent in component._parent_components:
                    if parent not in ret_val:
                        component_queue.append(parent)
        return list(ret_val)

    def print_status_tree(self) -> None:
        tree = self.get_status_tree()
        rich_print(tree)

    def get_status_tree(self, parent_tree: Tree = None) -> Tree:
        self_tree = Tree(f"Component: {self.identifier}")
        if parent_tree is not None:
            parent_tree.add(self_tree)
        for dep_attr_name, dep_component in self.dependencies.items():
            dep_component.get_status_tree(parent_tree=self_tree)
        return self_tree
