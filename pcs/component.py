import abc
import importlib
import logging
import sys
import uuid
from hashlib import sha1
from pathlib import Path
from typing import Any, Type, TypeVar

from dill.source import getsource as dill_getsource
from rich import print as rich_print
from rich.tree import Tree

from pcs.argument_set import ArgumentSet
from pcs.component_run import Output
from pcs.registry import Registry
from pcs.repo import GitHubRepo, LocalRepo, Repo
from pcs.run_command import Command
from pcs.spec_object import Component
from pcs.utils import parse_github_web_ui_url
from pcs.virtual_env import NoOpVirtualEnv, VirtualEnv

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ObjectManager(abc.ABC, Component):
    """
    ObjectManagers manage an underlying Python object (i.e. a module, class,
    or class instance). They can also run a method that is an attribute on
    their underlying object. Runs can take an argument set.
    """
    def __init__(self):
        Component.__init__(self)
        self.active_output = None

    def get_default_function_name(self):
        try:
            imported_obj = self.get_object()
            entry_point = imported_obj.DEFAULT_ENTRY_POINT
        except AttributeError:
            entry_point = "run"
        return entry_point

    def run(self, entry_point: str, *args, **kwargs):
        """
        Run an entry point with provided arguments. If you need to specify
        arguments to the init function of the managed object or any of
        its dependency components, use :py:func:`run_with_arg_set`.

        :param entry_point: name of function to call on manage object.
        :param kwargs: keyword-only args to pass through to managed object
            function called entry-point.
        :return: the return value of the entry point called.
        """
        run = self.run_with_arg_set(
            entry_point,
            args=ArgumentSet(args, kwargs),
            log_return_value=True,
        )
        return run.return_value

    def run_with_arg_set(
        self,
        function_name: str,
        arg_set: ArgumentSet = None,
        publish_to: Registry = None,
        log_return_value: bool = True,
        return_value_log_format: str = "yaml",
    ) -> Output:
        """
        Run the specified entry point a new instance of this Module's
        managed object given the specified arg_set, log the results
        and return the Run object.

        :param function_name: Name of a function to be called on a new
            instance of this component's managed object.
        :param arg_set: A :py:func:`pcs.argument_set.ArgumentSet` or
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
        assert not self.active_output, (
            f"Module {self.identifier} already has an active_output, so a "
            "new run is not allowed."
        )
        arg_set = arg_set if arg_set else ArgumentSet()
        command = Command(self, function_name, arg_set, log_return_value)
        with Output.from_command(command) as output:
            for c in self.dependency_list():
                c.active_output = output
            obj = self.get_object()
            res = self.call_function_with_arg_set(obj, function_name, arg_set)
            if log_return_value:
                output.log_return_value(res, return_value_log_format)
            for c in self.dependency_list():
                c.active_output = None
            if publish_to:
                output.to_registry(publish_to)
            return output

    def call_function_with_arg_set(
        self, instance: Any, function_name: str, arg_set: ArgumentSet
    ) -> Any:
        fn = getattr(instance, function_name)
        assert fn is not None, f"{instance} has no attr {function_name}"
        print(f"Calling {self.identifier}.{function_name} with "
              f"args: {arg_set.args} and kwargs: {arg_set.kwargs})")
        result = fn(*arg_set.args, **arg_set.kwargs)
        return result

    @abc.abstractmethod
    def get_object(self) -> Any:
        raise NotImplementedError


class Module(ObjectManager):
    """
    A Module is an object manager. Objects can be Python Modules, Python
    Classes, or Python Class Instances. The Module abstraction provides a
    standard programmatic mechanism for managing dependencies between these
    objects, reproducibly creating/initializing them and executing their
    methods. You can think of methods on a managed object as "managed methods"
    which we call "Entry Points". We call the execution of an Entry Point a
    "Run". Components provide reproducibility by automatically tracking (i.e.,
    logging) all of the parts that make up a Run, including: (1) the code of
    the object being run (i.e., the Module and its Entry Point), (2) the
    full DAG of other objects it depends on (i.e., DAG of other Components),
    (3) the set of arguments (literally a
    :py:func:`pcs.argument_set.ArgumentSet`) used during initialization of
    the managed object and all objects it transitively depends on, and
    (4) the arguments passed to the Entry Point being run.
    """

    DUNDER_NAME = "__component__"

    def __init__(
        self,
        repo: Repo,
        file_path: str,
        version: str = None,
        requirements_path: str = None,
        **other_dependencies,
    ):
        """
        :param repo: Repo where this Module's source file can be found. The
            ``file_path`` argument is relative to the root this Repo.
        :param file_path: Path to Python module file this Module manages.
        :param class_name: Optionally, the name of the class that is being
            managed. If none provided, then by default this is a
            managed Python Module.
        :param requirements_path: Optional path to a pip installable file.
        :param other_dependencies: List of other Components this depends on.
        """
        super().__init__()
        for k, v in other_dependencies.items():
            setattr(self, k, v)
        self.register_attributes(other_dependencies.keys())
        self.repo = repo
        self.file_path = file_path
        self.version = version
        self.requirements_path = requirements_path
        self.register_attributes(
            ["repo", "file_path", "version", "requirements_path"]
        )
        self._venv = None
        self._requirements = []
        self._parent_modules = set()
        self._use_venv = True

    @classmethod
    def from_github_registry(
        cls,
        github_url: str,
        identifier: str,
    ) -> "Module":
        """
        This method gets a Module from a registry file found on GitHub.  If
        the registry file contains a LocalRepo, this method automatically
        translates that LocalRepo into a GitHubRepo.

        The ``github_url`` argument can be found by navigating to the
        registry file on the GitHub web UI.  It should look like the
        following::

            https://github.com/<project>/<repo>/{blob,raw}/<branch>/<path>
        """
        project, repo_name, branch, reg_file_path = parse_github_web_ui_url(
            github_url
        )
        repo = Repo.from_github(project, repo_name)
        registry = Registry.from_file_in_repo(repo, reg_file_path, branch)
        module = cls.from_registry(registry, identifier)
        return module

    @classmethod
    def from_repo(
        cls,
        repo: Repo,
        version: str,
        file_path: str,
        class_name: str = None,
        requirements_path: str = None,
    ) -> "Module":
        full_path = repo.get_local_file_path(file_path, version)
        assert full_path.is_file(), f"{full_path} does not exist"
        return cls(
            repo=repo,
            class_name=class_name,
            file_path=file_path,
            version=version,
            requirements_path=requirements_path,
        )

    def get_object(self):
        collected = {}
        return self._get_object(collected)

    def _get_object(self, collected: dict) -> T:
        if self.identifier in collected:
            return collected[self.identifier]
        mod = self._import_module()
        #mod_deps = self.dependencies(filter_by_types=[Module]).items()
        #for dep_attr_name, dep_module in mod_deps:
        #    print(f"Adding {dep_attr_name} to {self.identifier}")
        #    dep_mod = dep_module._get_object(
        #        arg_set=arg_set, collected=collected
        #    )
        return mod

    def _import_module(self):
        """Return managed module, or class if ``self.class_name`` is set."""
        if not self._venv:
            self._venv = self._build_virtual_env()
            self._venv.activate()
        full_path = self.repo.get_local_file_path(self.file_path, self.version)
        assert full_path.is_file(), f"{full_path} does not exist"
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE", str(full_path)
        )
        managed_obj = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(full_path.parent))
        spec.loader.exec_module(managed_obj)
        return managed_obj

    def _build_virtual_env(self) -> VirtualEnv:
        # Only the root Module will setup and activate the VirtualEnv
        if not self._use_venv or self._parent_modules:
            return NoOpVirtualEnv()
        req_paths = set()
        for c in self.dependency_list(include_parents=True):
            if not isinstance(c, Module):
                continue  # Only process dependencies that are other Modules
            if c.requirements_path is None:
                continue
            for req_path in str(c.requirements_path).split(";"):
                full_req_path = self.repo.get_local_file_path(
                    req_path, c.version
                ).absolute()
                req_paths.add(full_req_path)
        return VirtualEnv.from_requirements_paths(req_paths)

    def _handle_repo_spec(self, repos):
        existing_repo = repos.get(self.repo.name)
        if existing_repo:
            if self.repo.to_dict() != existing_repo:
                self.repo.name = str(uuid.uuid4())
        repos[self.repo.name] = self.repo.to_dict()

    def to_versioned_module(self, force: bool = False) -> "Module":
        repo_url, version = self.repo.get_version_from_git(
            self.file_path, version=self.version, force=force
        )
        prefixed_file_path = self.repo.get_prefixed_path_from_repo_root(
            version, self.file_path
        )
        prefixed_reqs_path = None
        if self.requirements_path:
            prefixed_reqs_path = self.repo.get_prefixed_path_from_repo_root(
                version, self.requirements_path
            )
        clone = Module(
            repo=GitHubRepo(url=repo_url),
            file_path=prefixed_file_path,
            version=version,
            requirements_path=prefixed_reqs_path,
        )
        for attr_name, dependency in self.dependencies().items():
            frozen_dependency = dependency.to_versioned_module(force=force)
            clone.add_dependency(frozen_dependency, attribute_name=attr_name)
        return clone

    def to_frozen_registry(self, force: bool = False) -> Registry:
        versioned = self.to_versioned_module(force)
        return versioned.to_registry()

    def print_status_tree(self) -> None:
        tree = self.get_status_tree()
        rich_print(tree)

    def get_status_tree(self, parent_tree: Tree = None) -> Tree:
        self_tree = Tree(f"Module: {self.identifier}")
        if parent_tree is not None:
            parent_tree.add(self_tree)
        for dep_attr_name, dep_module in self.dependencies().items():
            dep_module.get_status_tree(parent_tree=self_tree)
        return self_tree


class Class(ObjectManager):
    def __init__(self, module: Module, class_name: str, **other_dependencies):
        super().__init__()
        for k, v in other_dependencies.items():
            setattr(self, k, v)
        self.register_attributes(other_dependencies.keys())
        self.module = module
        self.class_name = class_name
        self.register_attributes(["module", "class_name"])

    @classmethod
    def from_class(
        cls,
        class_obj: Type[T],
        repo: Repo = None,
    ) -> "Module":
        if class_obj.__module__ == "__main__":
            # handle classes defined in REPL.
            file_contents = dill_getsource(class_obj)
            if not repo:
                repo = LocalRepo()
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
            file_path=src_file.name,
            class_name=class_obj.__name__,
        )

    def get_object(self):
        module = self.module.get_object()
        return getattr(module, self.class_name)


class Instance(ObjectManager):
    """
    An Instance Component is very similar to a Class Component. The difference
    is that for an Instance, the underlying class is instantiated during
    initialization of the component.
    """
    def __init__(
        self,
        instance_of: Class,
        argument_set: ArgumentSet,
    ):
        super().__init__()
        self.instance_of = instance_of
        self.argument_set = argument_set
        self.register_attributes(["instance_of", "argument_set"])

    def get_object(self):
        cls = self.instance_of.get_object()
        return cls(*self.argument_set.args, **self.argument_set.kwargs)
