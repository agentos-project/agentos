import json
import yaml
from deepdiff import DeepDiff
from hashlib import sha1
from typing import Collection, Dict, List, Mapping, Union
from pcs.registry import Registry, InMemoryRegistry
from pcs.specs import flatten_spec


#class SpecMeta(type):
#    def __new__(mcs, name, parents, namespace):
#        o = type.__new__(mcs, name, parents, namespace)
#        orig_init = o.__init__
#
#        def new_init(self, *args, **kwargs):
#            print("in new_init")
#            assert args == {}, (
#                "Positional parameters are not allowed in the __init__() "
#                "method of a SpecObject, only Keyword parameters."
#            )
#            for k, v in kwargs.items():
#                print(f"setting attribute {k} = {v}")
#                setattr(self, k, v)
#            orig_init(self, *args, *kwargs)
#
#        o.__init__ = new_init
#        return o


class SpecObject:
    """
    A SpecObject is a Python class whose instances can serialize themselves
    to and from spec YAML strings and registry objects.

    A SpecObject is the Python object version of a PCS Spec, which itself
    is a YAML dictionary that maps content hash identifier string to
    "spec contents". The contents are in turn a str->str map.

    A value in the spec contents map can be another Spec's identifier.
    This represents a causal dependency between the two Specs.
    """
    def __init__(self):
        self._spec_attr_names: List[str] = []  # Managed by register_attribute
        self._spec_attr_types: Dict[str: Union[str, "SpecObject"]] = {}
        self.type = self.__class__.__name__
        self.register_attribute("type")

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(self)
        else:
            return NotImplemented

    def __str__(self) -> str:
        return self.identifier

    def __hash__(self) -> int:
        return int(self._sha1(), 16)

    def _sha1(self) -> str:
        # Not positive if this is stable across architectures.
        # See https://stackoverflow.com/q/27522626
        return sha1(self.to_sorted_dict_str().encode("utf-8")).hexdigest()

    def to_sorted_dict_str(self) -> str:
        # See https://stackoverflow.com/a/22003440
        return json.dumps(self.attributes, sort_keys=True)

    def register_attribute(self, attribute_name: str):
        # TODO: check that all attributes in self._spec_attr_names can be
        #       cleanly serialized into YAML.
        # TODO: Handle attributes that have default values.
        # TODO: Handle optional attributes (i.e., default value = None)
        # TODO: Handle dependency attributes (i.e., an attribute whose value
        #       must be another SpecObject), e.g. Component.repo, also
        #       ComponentRun.argument_set.
        # TODO: Component(SpecObject) should have its own functionality for
        #       handling its dependencies on other components. This
        #       functionality lives in Component.get_object() and similar
        #       functions that need to use the spec attributes
        #       to do things like pass values into managed object __init__()
        #       functions, manipulate calls to __import__() (in the case of
        #       module components). These special attributes are
        #       dictionaries from attribute name to other SpecObject, e.g.,
        #       Component.dependencies.
        #       ComponentRun(SpecObject) also needs do something similar when
        #       it passes arguments into an entry point being run.
        assert attribute_name not in self.attributes
        assert hasattr(self, attribute_name)
        attr = getattr(self, attribute_name)
        assert type(attr) is str or isinstance(attr, SpecObject)
        self._spec_attr_types[attribute_name] = type(attr)
        self._spec_attr_names.append(attribute_name)

    def register_attributes(self, attribute_names: Collection[str]):
        for name in attribute_names:
            self.register_attribute(name)

    @property
    def identifier(self) -> str:
        return self._sha1()

    @property
    def attributes(self) -> Dict:
        return {name: getattr(self, name) for name in self._spec_attr_names}

    @property
    def dependencies(self) -> List:
        """
        Returns the subset of ``self.attributes`` that are references to
        other SpecObjects.
        """
        return [
            getattr(self, name) for name, type
            in self._spec_attr_types.items()
            if isinstance(type, SpecObject)
        ]

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
                "trying to add. Diff of existing spec vs this spec:\n\n {diff}"
            )
        if not dry_run:
            self._all_dependencies_to_registry(registry, False)
            registry.add_spec(self.to_spec())
        return registry

    def _all_dependencies_to_registry(self, registry: Registry, dry_run: bool):
        deps = self.dependencies
        dry_run_text = "Dry running " if dry_run else "Actually "
        print(
            f"{dry_run_text}pushing dependencies of {self.identifier} "
            f"({deps}) to registry {registry}."
        )
        for d in deps:
            d.to_registry(
                registry=registry,
                recurse=True,
                dry_run=dry_run,
            )

    def from_registry(self, registry: Registry, identifier: str):
        raise NotImplementedError

    def to_spec(self, flatten: bool = False) -> Dict:
        spec = {self.identifier: self.attributes}
        return flatten_spec(spec) if flatten else spec

    def to_yaml(self) -> str:
        return yaml.dump(self.to_spec())

    @staticmethod
    def from_spec(self, spec: Mapping, registry: Registry = None) -> Mapping:
        return NotImplementedError

    def publish(self) -> Registry:
        self.to_registry(Registry.from_default())


def test_spec_object():
    class RepoSpec(SpecObject):
        def __init__(self, repo_type: str, url: str):
            super().__init__()
            self.repo_type = repo_type
            self.url = url
            self.register_attributes(["repo_type", "url"])

    r = RepoSpec(
        repo_type="github", url="https://github.com/agentos-project/agentos"
    )
    assert r.type == "RepoSpec"
    assert r.repo_type == "github"
    print(r.to_spec())
    print(r.to_registry().to_yaml())
