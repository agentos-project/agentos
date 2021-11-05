import importlib
from pathlib import Path
import sys
import yaml
from enum import Enum
from typing import TypeVar, Dict, Type

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class RepoType(Enum):
    LOCAL = "local"
    GITHUB = "github"
    IN_MEMORY = "in_memory"


class Repo:
    pass


class GitHubRepo(Repo):
    def __init__(self, url: str, default_version: str = None):
        """If ``default_version`` is not provided, HEAD of master will be
        used."""
        self.type = RepoType.GITHUB
        self.url = url
        self.default_version = default_version


class LocalRepo(Repo):
    def __init__(self, file_path: str):
        self.type = RepoType.LOCAL
        self.file_path = Path(file_path)


class InMemoryRepo(Repo):
    def __init__(self):
        self.type = RepoType.IN_MEMORY


class ComponentNamespace:
    """
    Associates names (as one might find in the agentos.yaml) to Component
    objects.
    """

    def __init__(self):
        self.repos = {}
        self.components = {}
        self.dependency_names = {}

    def add_repo(self, name: str, repo: "Repo"):
        self.repos[name] = repo

    def add_component(self, name: str, component: "Component"):
        self.components[name] = component

    def add_params(self, component_name: str, fn_name: str, params: Dict):
        component = self.components.get(component_name)
        if component is None or params is None:
            return
        component.add_params(fn_name, params)

    def get_component(self, name: str) -> "Component":
        """Gets the Component associated with ``name``. Guarantees the
        Component's dependency DAG is properly hooked up."""
        rehydrate_list = [name]
        while len(rehydrate_list) > 0:
            curr_name = rehydrate_list.pop(0)
            curr_component = self.components[curr_name]
            dependency_names = self.dependency_names[curr_name]
            for alias, dependency_name in dependency_names.items():
                dependency = self.components[dependency_name]
                curr_component.add_dependency(dependency, alias=alias)
                rehydrate_list.append(dependency_name)
        return self.components[name]

    def parse_param_file(self, param_file: str) -> None:
        """Parses a param file and adds the parameters to the appropriate
        Component methods."""
        if param_file is None:
            return
        with open(param_file) as file_in:
            param_yaml = yaml.safe_load(file_in)
        for c_name, param_dict in param_yaml.items():
            for fn_name, fn_params in param_dict.items():
                self.add_params(c_name, fn_name, fn_params)

    def parse_spec_file(self, spec_file: str) -> None:
        """Parses a spec file and adds all Repos and Components to this
        namespace."""
        with open(spec_file) as file_in:
            config = yaml.safe_load(file_in)
        self._parse_repos(config.get("repos", {}))
        self._parse_components(config.get("components", {}))

    def _parse_repos(self, repos_spec: Dict) -> None:
        for name, spec in repos_spec.items():
            self.repos[name] = spec
            if spec["type"] == RepoType.LOCAL.value:
                repo = LocalRepo(spec["path"])
                self.add_repo(name, repo)
            elif spec["type"] == RepoType.GITHUB.value:
                raise NotImplementedError()
            elif spec["type"] == RepoType.IN_MEMORY.value:
                raise NotImplementedError()
            else:
                raise NotImplementedError()

    def _parse_components(self, components_spec: Dict) -> None:
        for name, spec in components_spec.items():
            cls = self._get_managed_class(
                spec["class_name"], spec["repo"], spec["file_path"]
            )
            component = Component(managed_cls=cls)
            self.add_component(name, component)
            self.dependency_names[name] = spec.get("dependencies", {})

    def _get_managed_class(
        self, class_name: str, repo_name: str, file_path: str
    ) -> Type[T]:
        repo = self.repos[repo_name]
        module_path = repo.file_path / Path(file_path)
        assert module_path.is_file(), f"{module_path} does not exist"
        sys.path.append(str(module_path.parent))
        spec = importlib.util.spec_from_file_location(
            f"AOS_MODULE_{class_name.upper()}", str(module_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, class_name)
        sys.path.pop()
        return cls


class Component:
    """
    A Component is a class manager. It provides a standard way for runtime and
    code implementations to communicate about parameters, entry points, and
    dependencies.
    """

    def __init__(
        self, managed_cls: Type[T], dunder_name: str = "__component__"
    ):
        self._managed_cls = managed_cls
        self._dunder_name = dunder_name
        self._requirements = []
        self._dependencies = {}
        self._params = {}
        self._instance = None

    @classmethod
    def get_from_yaml(
        cls,
        component_name: str,
        component_spec_file: str,
        param_file: str = None,
    ) -> "Component":
        ns = ComponentNamespace()
        ns.parse_spec_file(component_spec_file)
        ns.parse_param_file(param_file)
        return ns.get_component(component_name)

    @classmethod
    def get_from_class(
        cls,
        managed_cls: Type[T],
        dunder_name: str = "__component__",
    ) -> "Component":
        return Component(
            managed_cls=managed_cls,
            dunder_name=dunder_name,
        )

    @property
    def name(self):
        return self._managed_cls.__name__

    def call(self, fn_name: str):
        self.instantiate_class()
        fn = getattr(self._instance, fn_name)
        assert fn is not None, f"{self._instance} has no function {fn_name}"
        params = self._params.get(fn_name, {})
        print(f"Calling {self.name}.{fn_name}(**{params})")
        return fn(**params)

    def add_params(self, fn_name: str, params: Dict):
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
            dep_component.instantiate_class()
            setattr(self._instance, dep_alias, dep_component._instance)
        setattr(self._instance, self._dunder_name, self)
        self._managed_cls.__init__ = save_init
        self.call("__init__")

    def get_instance(self) -> T:
        self.instantiate_class()
        return self._instance
