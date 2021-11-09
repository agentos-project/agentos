import importlib
from pathlib import Path
import sys
import yaml
from enum import Enum
from typing import TypeVar, Dict, Type, Any

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class RepoType(Enum):
    LOCAL = "local"
    GITHUB = "github"
    IN_MEMORY = "in_memory"


class Repo:
    pass


class GitHubRepo(Repo):
    def __init__(self, name: str, url: str, default_version: str = None):
        """If ``default_version`` is not provided, HEAD of master will be
        used."""
        self.name = name
        self.type = RepoType.GITHUB
        self.url = url
        self.default_version = default_version


class LocalRepo(Repo):
    def __init__(self, name: str, file_path: str):
        self.name = name
        self.type = RepoType.LOCAL
        self.file_path = Path(file_path)


class InMemoryRepo(Repo):
    def __init__(self):
        self.type = RepoType.IN_MEMORY


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about parameters, entry points, and
    dependencies.
    """

    def __init__(
        self,
        managed_cls: Type[T],
        name: str = None,
        dunder_name: str = "__component__",
    ):
        self._managed_cls = managed_cls
        self._dunder_name = dunder_name
        self._requirements = []
        self._dependencies = {}
        self._params = {}
        self._instance = None
        self.name = name if name else self._managed_cls.__name__

    @classmethod
    def get_from_yaml(
        cls,
        name: str,
        component_spec_file: str,
    ) -> "Component":
        components = cls.parse_spec_file(component_spec_file)
        return components[name]

    @classmethod
    def get_from_class(
        cls, managed_cls: Type[T], name: str = None
    ) -> "Component":
        return Component(managed_cls=managed_cls, name=name)

    @classmethod
    def get_from_file(
        cls, class_name: str, file_path: str, name: str = None
    ) -> "Component":
        assert file_path.is_file(), f"{file_path} does not exist"
        sys.path.append(str(file_path.parent))
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE_{class_name.upper()}", str(file_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, class_name)
        sys.path.pop()
        return Component(managed_cls=cls, name=name)

    def parse_param_file(self, param_file: str) -> None:
        """Parses a param file and adds the parameters to the appropriate
        Component methods."""
        if param_file is None:
            return
        with open(param_file) as file_in:
            params = yaml.safe_load(file_in)
        self.add_params(params)

    def add_params(self, params: Dict):
        for c_name, param_dict in params.items():
            component = self.get_dependency_with_name(c_name)
            for fn_name, fn_params in param_dict.items():
                if component is None or fn_params is None:
                    continue
                component.add_params_to_fn(fn_name, fn_params)

    def get_dependency_with_name(self, name: str):
        """Searches the Component dependency DAG rooted at ``self`` for a
        component named ``name``.  Note, the root component's name (``self``)
        will also be checked."""
        if self.name == name:
            return self
        for dep_name, dep_component in self._dependencies.items():
            found = dep_component.get_dependency_with_name(name)
            if found:
                return found
        return None

    def call(self, fn_name: str):
        self.instantiate_class()
        fn = getattr(self._instance, fn_name)
        assert fn is not None, f"{self._instance} has no function {fn_name}"
        params = self._params.get(fn_name, {})
        print(f"Calling {self.name}.{fn_name}(**{params})")
        return fn(**params)

    def add_params_to_fn(self, fn_name: str, params: Dict[str, Any]):
        print(f"{self.name}: adding {params} to {fn_name}()")
        curr_params = self._params.get(fn_name, {})
        curr_params.update(params)
        self._params[fn_name] = curr_params

    def add_dependency(self, component: "Component", alias: str = None):
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if alias is None:
            alias = component.name
        self._dependencies[alias] = component

    def instantiate_class(self) -> None:
        if self._instance is not None:
            return
        save_init = self._managed_cls.__init__
        self._managed_cls.__init__ = lambda self: None
        self._instance = self._managed_cls()
        for dep_alias, dep_component in self._dependencies.items():
            print(f"Adding {dep_alias} to {self.name}")
            dep_component.instantiate_class()
            setattr(self._instance, dep_alias, dep_component._instance)
        setattr(self._instance, self._dunder_name, self)
        self._managed_cls.__init__ = save_init
        self.call("__init__")

    def get_instance(self) -> T:
        self.instantiate_class()
        return self._instance

    @classmethod
    def parse_spec_file(cls, spec_file: str) -> None:
        """Returns all Repos and Components defined by this ``spec_file``."""
        with open(spec_file) as file_in:
            config = yaml.safe_load(file_in)
        repos = cls._parse_repos(config.get("repos", {}))
        components = cls._parse_components(config.get("components", {}), repos)
        return components

    @classmethod
    def _parse_repos(cls, repos_spec: Dict) -> None:
        repos = {}
        for name, spec in repos_spec.items():
            repos[name] = spec
            if spec["type"] == RepoType.LOCAL.value:
                repo = LocalRepo(name=name, file_path=spec["path"])
                repos[name] = repo
            elif spec["type"] == RepoType.GITHUB.value:
                raise NotImplementedError()
            elif spec["type"] == RepoType.IN_MEMORY.value:
                raise NotImplementedError()
            else:
                raise NotImplementedError()
        return repos

    @classmethod
    def _parse_components(cls, components_spec: Dict, repos: Dict) -> None:
        components = {}
        dependency_names = {}
        for name, spec in components_spec.items():
            repo = repos[spec["repo"]]
            full_path = repo.file_path / Path(spec["file_path"])
            component = Component.get_from_file(
                class_name=spec["class_name"], file_path=full_path, name=name
            )
            components[name] = component
            dependency_names[name] = spec.get("dependencies", {})

        # Wire up the dependency graph
        for name, component in components.items():
            for alias, dependency_name in dependency_names[name].items():
                dependency = components[dependency_name]
                component.add_dependency(dependency, alias=alias)

        return components
