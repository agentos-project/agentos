from typing import Dict
from agentos.utils import DUMMY_DEV_REGISTRY
from agentos.component import Component
from agentos.repo import Repo


def get_component(name: str) -> Component:
    registry = Registry()
    return registry.get_component(name)


class Registry:
    """
    This encapsulates interactions with an external registry that contains
    information about publicly-available Components.
    """

    def __init__(self, registry=None):
        self.registry = registry if registry else DUMMY_DEV_REGISTRY
        self.latest_refs = self.registry["latest_refs"]

    def get_component(self, name: str) -> Component:
        instantiated = {}
        identifier = Component.Identifier(name, self.latest_refs)
        return self._get_component(identifier, instantiated)

    def _get_component(
        self, identifier: Component.Identifier, instantiated: Dict
    ) -> Component:
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
        for attr_name, dep_name in component_spec["dependencies"].items():
            dep_id = Component.Identifier(dep_name, self.latest_refs)
            dep_component = self._get_component(dep_id, instantiated)
            component.add_dependency(dep_component, attribute_name=attr_name)
        return component
