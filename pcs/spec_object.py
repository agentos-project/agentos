from typing import Collection, Dict, List, Mapping
import inspect
import logging

import yaml
from deepdiff import DeepDiff, DeepHash

from pcs.registry import InMemoryRegistry, Registry
from pcs.specs import flatten_spec

logger = logging.getLogger(__name__)


class Component:
    """
    A Component is a Python class whose instances can serialize themselves
    to and from spec YAML strings and registry objects.

    A SpecObject is the Python object version of a PCS Spec, which itself
    is a YAML dictionary that maps content hash identifier string to
    "spec contents". The contents are in turn a str->str map.

    A value in the spec contents map can be another Spec's identifier.
    This represents a causal dependency between the two Specs.
    """

    IDENTIFIER_ATTR_NAME = "identifier"
    TYPE_ATTR_NAME = "type"

    def __init__(self):
        """
        Assume this is called by child types after they have assigned values
        to all attributes they declared via their class 'ATTRIBUTES' variable.
        """
        assert hasattr(type(self), "ATTRIBUTES"), (
            "All Component Types must have a class member called 'ATTRIBUTES' "
            "of type List[str]"
        )
        assert Component.IDENTIFIER_ATTR_NAME not in self.ATTRIBUTES
        assert Component.TYPE_ATTR_NAME not in self.ATTRIBUTES
        self._identifier = ""  # Is updated by self.register_attributes()
        self._spec_attr_names: List[str] = []  # Managed by register_attribute
        # While this Component's identifier is not considered an attribute,
        # since it is a function of all attributes, it is included in this
        # Component's spec.
        self.register_attribute(self.TYPE_ATTR_NAME)
        self.register_attributes(self.ATTRIBUTES)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return NotImplemented

    def __str__(self) -> str:
        return self.identifier

    def __hash__(self) -> int:
        return int(self.sha1(), 16)

    def sha1(self) -> str:
        return DeepHash(self.attributes_as_strings, hasher=DeepHash.sha1hex)[
            self.attributes_as_strings
        ]

    def register_attribute(self, attribute_name: str):
        assert attribute_name != self.IDENTIFIER_ATTR_NAME, (
            f"{self.IDENTIFIER_ATTR_NAME} cannot be registered as an "
            "attribute since it is a function of all attributes."
        )
        assert attribute_name not in self._spec_attr_names
        assert hasattr(self, attribute_name)
        attr = getattr(self, attribute_name)
        assert isinstance(attr, str) or isinstance(attr, Component)
        self._spec_attr_names.append(attribute_name)
        self._identifier = self.sha1()

    def register_attributes(self, attribute_names: Collection[str]):
        for name in attribute_names:
            self.register_attribute(name)

    @classmethod
    @property
    def type(cls):
        return cls.__name__

    @property
    def identifier(self) -> str:
        return self.sha1()

    @property
    def attributes(self) -> Dict:
        return {name: getattr(self, name) for name in self._spec_attr_names}

    @property
    def attributes_as_strings(self) -> Dict:
        attr_strings = {}
        for name in self._spec_attr_names:
            v = getattr(self, name)
            attr_val_as_str = v if isinstance(v, str) else v.identifier
            attr_strings[name] = attr_val_as_str
        return attr_strings

    @property
    def dependencies(self) -> List:
        """
        Returns the subset of ``self.attributes`` that are references to
        other SpecObjects.
        """
        return {
            name: value
            for name, value in self.attributes.items()
            if isinstance(value, Component)
        }

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        dry_run: bool = False,
    ) -> Registry:
        if not registry:
            registry = InMemoryRegistry()
        if recurse:
            # Test whether recursively pushing all dependencies will succeed.
            self._all_dependencies_to_registry(registry, True)
        existing = registry.get_spec(self.identifier, error_if_not_found=False)
        # Test whether pushing this spec to registry will succeed.
        if existing:
            diff = DeepDiff(existing, self.to_spec())
            assert not diff, (
                f"A spec with identifier '{self.identifier}' already exists "
                f"in registry '{registry}' and differs from the one you're "
                f"trying to add. Diff of existing spec vs this spec:\n {diff}"
            )
        if not dry_run:
            self._all_dependencies_to_registry(registry, False)
            registry.add_spec(self.to_spec())
        return registry

    def _all_dependencies_to_registry(self, registry: Registry, dry_run: bool):
        dep_objs = self.dependencies.values()
        dry_run_text = "Dry running " if dry_run else "Actually "
        logger.debug(
            f"{dry_run_text}pushing dependencies of {self.identifier} "
            f"({dep_objs}) to registry {registry}."
        )
        for d in dep_objs:
            d.to_registry(
                registry=registry,
                recurse=True,
                dry_run=dry_run,
            )

    @classmethod
    def from_registry(cls, registry: Registry, identifier: str):
        return cls.from_spec(registry.get_spec(identifier))

    def to_spec(self, flatten: bool = False) -> Dict:
        spec = {self.identifier: self.attributes_as_strings}
        return flatten_spec(spec) if flatten else spec

    def to_yaml(self) -> str:
        return yaml.dump(self.to_spec())

    @classmethod
    def from_spec(cls, spec: Mapping, registry: Registry = None) -> Mapping:
        raise NotImplementedError
        #flat_spec = flatten_spec(spec)
        #kwargs = [attr_name: flat_spec[attr_name] for attr_name in cls.
        #return cls(
        #    flat_spec[cls.IDENTIFIER_ATTR_NAME],
        #    url=flat_spec[RepoSpecKeys.URL],
        #)

    def publish(self) -> Registry:
        self.to_registry(Registry.from_default())


def test_spec_object():
    class GitHubComponent(Component):
        ATTRIBUTES = ["url"]

        def __init__(self, url: str):
            self.url = url
            super().__init__()

    r = GitHubComponent(url="https://github.com/agentos-project/agentos")
    assert r.type == "GitHubComponent"

    class ModuleComponent(Component):
        ATTRIBUTES = ["repo", "version", "module_path"]

        def __init__(self, repo: GitHubComponent, version: str, module_path: str):
            self.repo = repo
            self.version = version
            self.module_path = module_path
            super().__init__()

    c = ModuleComponent(
        repo=r, version="master", module_path="example_agents/random/agent.py"
    )
    assert c.repo is r
    reg = c.to_registry()
    print(reg.to_yaml())
    print("=======")
    print(c.to_registry(reg))
    print("=======")
    c_two = ModuleComponent(
        repo=r, version="master", module_path="example_agents/random/agent.py"
    )
    print(c_two.to_registry(reg))
