import copy
import json
from hashlib import sha1
from typing import List, Mapping, Collection
from agentos.registry import Registry, InMemoryRegistry
from agentos.specs import flatten_spec

class SpecObject:
    """
    A SpecObject is the Python object version of a Spec. A Spec itself
    is a YAML dictionary that maps an Identifier string to "spec contents"
    which itself is a str->str map.

    A value in the spec contents map can be another Spec's identifiers.
    This represents a causal dependency between the two Specs.

    A SpecObject is a python class whose instances can serialize themselves
    to and from spec YAML strings and also registry objects.
    """
    def __init__(
        self,
        register_spec_type: bool = True,
        register_init_params: bool = True
    ):
        self._spec_attr_names: List[str] = []  # Managed by register_attribute
        if register_spec_type:
            self.spec_type = self.__class__.__name__
            self.register_attribute("spec_type")
        

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
        return json.dumps(self.contents, sort_keys=True)

    def register_attribute(self, attribute_name: str):
        # TODO: check that all attributes in self._spec_attr_names can be
        #       cleanly serialized into YAML.
        # TODO: Handle spec_attributes that have default values.
        # TODO: Handle optional spec_attributes (i.e., default value = None)
        # TODO: Handle dependency attributes (i.e., an attribute whose value
        #       must be another SpecObject), e.g. Component.repo, also
        #       ComponentRun.argument_set.
        # TODO: Component(SpecObject) should have its own functionality for
        #       handling its dependencies on other components. This
        #       functionality lives in Component.get_object() and similar
        #       functions that need to use the spec attributes
        #       to do things like pass values into managed object __init__()
        #       functions, manipulate calls to __import__() (in the case of
        #       module components). These special spec_attributes are
        #       dictionaries from attribute name to other SpecObject, e.g.,
        #       Component.dependencies.
        #       ComponentRun(SpecObject) also needs do something similar when
        #       it passes arguments into an entry point being run.
        assert attribute_name not in self.spec_attributes
        assert hasattr(self, attribute_name)
        self._spec_attr_names.append(attribute_name)

    def register_attributes(self, attribute_names: Collection[str]):
        for name in attribute_names:
            self.register_attribute(name)

    @property
    def identifier(self) -> str:
        return self._sha1()

    @property
    def spec_attributes(self) -> Mapping:
        return {
            name: copy.deepcopy(getattr(self, name))
            for name in self._spec_attr_names
        }

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        force: bool = False,
    ) -> Registry:
        if not registry:
            registry = InMemoryRegistry()
        if recurse:
            # handle dependencies on other components
            l = self.dependency_list(include_root=False)
            print(f"dependency list of {self.name} is {l}")
            for c in l:

    def from_registry(self, registry: Registry, identifier: str):
        raise NotImplementedError

    def to_spec(self, flatten: bool = False) -> Mapping:
        spec = {self.identifier: self.spec_attributes}
        return flatten_spec(spec) if flatten else spec

    @staticmethod
    def from_spec(self, spec: Mapping, registry: Registry = None) -> Mapping:
        return NotImplementedError

    def publish(self):
        self.to_registry(Registry.from_default())


class ExampleSpec(SpecObject):
