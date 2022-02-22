import json
import inspect
from hashlib import sha1
from typing import Mapping
from agentos.registry import Registry, InMemoryRegistry
from agentos.specs import flatten_spec

class SpecMeta(type):
    def __run__(cls, name, bases, classdict):
        obj = cls.__run__(name, bases, classdict)
        for
        obj.

class SpecObject(metaclass=SpecMeta):
    """
    A SpecObject is the Python object version of a Spec. A Spec itself
    is a YAML dictionary that maps an Identifier string to "spec contents"
    which itself is a str->str map.

    A value in the spec contents map can be another Spec's identifiers.
    This represents a causal dependency between the two Specs.

    A SpecObject is a python class whose instances can serialize themselves
    to and from spec YAML strings and also registry objects.
    """
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

    @property
    def identifier(self) -> str:
        return self._sha1()

    @property
    def contents(self) -> Mapping:
        sig = inspect.signature(self.__init__)
        sig.parameters

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
        spec = {self.identifier: self._contents}
        return flatten_spec(spec) if flatten else spec

    def from_spec(self, registry: Registry = None) -> Mapping:
        raise NotImplementedError
