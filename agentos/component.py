import importlib
from pathlib import Path
import sys
import yaml
import typing

# https://stackoverflow.com/a/44331733
T = typing.TypeVar("T")


class Repo:
    LOCAL_TYPE = "local"
    GITHUB_TYPE = "github"
    IN_MEMORY_TYPE = "memory"


class GitHubRepo(Repo):
    def __init__(self, url: str, default_version: str = None):
        """If not tag is provided, HEAD of master will be used."""
        self.url = url
        self.default_version = default_version


class LocalRepo(Repo):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)


class InMemoryRepo(Repo):
    pass


class ComponentNamespace:
    """The class associates names (as one might find in the agentos.yaml) to
    Component objects."""

    def __init__(self):
        self.repos = {}
        self.components = {}

    def add_repo(self, name: str, repo: "Repo"):
        self.repos[name] = repo

    def add_component(self, name: str, component: "Component"):
        self.components[name] = component

    def add_params(
        self, component_name: str, fn_name: str, params: typing.Dict
    ):
        component = self.components.get(component_name)
        if component is None or params is None:
            return
        component.add_params(fn_name, params)

    def get_component(self, name: str) -> "Component":
        """Gets the Component associated with [name]. Guarantees the
        Component's dependency DAG is properly hooked up."""
        component = self.components[name]
        rehydrate_list = [component]
        while len(rehydrate_list) > 0:
            curr = rehydrate_list.pop(0)
            for name in curr.dependency_names:
                curr.dependencies[name] = self.components[name]
                rehydrate_list.append(self.components[name])
        return component

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
        spec_path = Path(spec_file)
        with open(spec_path) as file_in:
            config = yaml.safe_load(file_in)
        self._parse_repos(config.get("repos", {}))
        self._parse_components(config.get("components", {}))

    def _parse_repos(self, repos_spec: typing.Dict) -> None:
        for name, spec in repos_spec.items():
            if spec["type"] == Repo.LOCAL_TYPE:
                repo = LocalRepo(spec["path"])
                self.add_repo(name, repo)
            elif spec["type"] == Repo.GITHUB_TYPE:
                raise NotImplementedError()
            elif spec["type"] == Repo.IN_MEMORY_TYPE:
                raise NotImplementedError()
            else:
                raise NotImplementedError()

    def _parse_components(self, components_spec: typing.Dict) -> None:
        for name, spec in components_spec.items():
            repo = self.repos[spec["repo"]]
            args = {**spec, "repo": repo}
            component = Component.get_from_spec(**args)
            self.add_component(name, component)


class Component:
    """
    A Component is a class manager. It allows standard way for runtime
    and code implementations to communicate about parameters, entry
    points, and dependencies.
    """

    def __init__(
        self,
        managed_cls: typing.Type[T],
        dependencies: typing.Dict[str, str] = None,
        requirements: typing.List[str] = None,
        dunder_name: str = "__component__",
    ):
        self.managed_cls = managed_cls
        self.dunder_name = dunder_name
        self.dependency_names = {} if dependencies is None else dependencies
        self.requirements = [] if requirements is None else requirements
        self.dependencies = {}
        self.params = {}
        self.instance = None

    @classmethod
    def get_from_spec(
        cls,
        repo: Repo,
        file_path: str,
        class_name: str,
        dependencies: typing.Dict[str, str] = None,
        requirements: typing.List[str] = None,
        dunder_name: str = "__component__",
    ) -> "Component":
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
        return Component(
            managed_cls=cls,
            dependencies=dependencies,
            requirements=requirements,
            dunder_name=dunder_name,
        )

    @classmethod
    def get_from_class(
        cls,
        managed_cls: typing.Type[T],
        dependencies: typing.Dict[str, str] = None,
        requirements: typing.List[str] = None,
        dunder_name: str = "__component__",
    ) -> "Component":
        return Component(
            managed_cls=managed_cls,
            dependencies=dependencies,
            requirements=requirements,
            dunder_name=dunder_name,
        )

    @property
    def name(self):
        return self.managed_cls.__name__

    def call(self, fn_name: str):
        self.instantiate_class()
        fn = getattr(self.instance, fn_name)
        assert fn is not None, f"{self.instance} has no function {fn_name}"
        params = self.params.get(fn_name, {})
        print(f"Calling {self.name}.{fn_name}(**{params})")
        return fn(**params)

    def add_params(self, fn_name: str, params: typing.Dict):
        print(f"{self.name}: adding {params} to {fn_name}()")
        curr_params = self.params.get(fn_name, {})
        curr_params.update(params)
        self.params[fn_name] = curr_params

    def add_dependency(self, component: "Component", alias: str = None):
        if type(component) is not type(self):
            raise Exception("add_dependency() must be passed a Component")
        if alias is None:
            alias = component.name
        self.dependencies[alias] = component
        self.dependency_names[alias] = component.name

    def instantiate_class(self) -> None:
        if self.instance is not None:
            return
        assert len(self.dependencies) == len(self.dependency_names)
        save_init = self.managed_cls.__init__
        self.managed_cls.__init__ = lambda self: None
        self.instance = self.managed_cls()
        for dep_alias, dep_component in self.dependencies.items():
            dep_component.instantiate_class()
            setattr(self.instance, dep_alias, dep_component.instance)
        setattr(self.instance, self.dunder_name, self)
        self.managed_cls.__init__ = save_init
        self.call("__init__")

    def get_instance(self) -> T:
        self.instantiate_class()
        return self.instance


# A REPL-ready demo
if __name__ == "__main__":

    class SimpleAgent:
        def __init__(self):
            env_name = self.env.__class__.__name__
            print(f"SimpleAgent: AgentOS added self.env: {env_name}")

        def reset_env(self):
            self.env.reset()

    class SimpleEnvironment:
        def reset(self):
            print("SimpleEnvironment.reset() called")

    # Generate Components from Classes
    agent_component = Component.get_from_class(SimpleAgent)
    environment_component = Component.get_from_class(SimpleEnvironment)

    # Add Dependency to SimpleAgent
    agent_component.add_dependency(environment_component, alias="env")

    # Instantiate a SimpleAgent and run reset_env() method
    agent = agent_component.get_instance()
    agent.reset_env()

    # Instantiate a ComponentNamespace
    ns = ComponentNamespace()

    # Add Components to the ComponentNamespace
    ns.add_component("agent", agent_component)
    ns.add_component("env", environment_component)

    # Get Components from ComponentNamespace
    ns_component = ns.get_component("agent")
    assert ns_component is agent_component
    assert ns_component.get_instance() is agent_component.get_instance()
