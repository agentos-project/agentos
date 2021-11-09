from agentos.utils import DUMMY_DEV_REGISTRY
from agentos.utils import ComponentIdentifier
from agentos.component import Component
from agentos.repo import Repo


def get_component(name):
    registry = Registry()
    return registry.get_component(name)


class Registry:
    def __init__(self, registry=None):
        self.registry = registry if registry else DUMMY_DEV_REGISTRY
        self.latest_refs = self.registry["latest_refs"]

    def get_component(self, name: str):
        instantiated = {}
        identifier = ComponentIdentifier(name, self.latest_refs)
        return self._get_component(identifier, instantiated)

    def _get_component(self, identifier, instantiated):
        if identifier.full in instantiated:
            return instantiated[identifier.full]
        component_spec = self.registry["components"][identifier.full]
        repo_name = component_spec["repo"]
        repo_spec = self.registry["repos"][repo_name]
        repo = Repo.from_spec(repo_name, repo_spec)
        component = Component.get_from_repo(
            repo=repo,
            identifier=identifier,
            class_name=component_spec["class_name"],
            file_path=component_spec["file_path"],
        )
        instantiated[identifier.full] = component
        for alias, dep_name in component_spec["dependencies"].items():
            dep_id = ComponentIdentifier(dep_name, self.latest_refs)
            dep_component = self._get_component(dep_id, instantiated)
            component.add_dependency(dep_component, alias=alias)
        return component
