import copy
import logging
import numbers
from typing import (
    TYPE_CHECKING,
    Collection,
    Dict,
    List,
    Mapping,
    Sequence,
    Type,
    TypeVar,
)

import yaml
from deepdiff import DeepDiff, DeepHash
from rich import print as rich_print
from rich.tree import Tree

import pcs  # for hasattr(pcs, ...)
from pcs.registry import InMemoryRegistry, Registry
from pcs.specs import Spec, flatten_spec, unflatten_spec
from pcs.utils import (
    copy_find_and_replace_leaves,
    extract_identifier,
    filter_leaves,
    is_identifier_ref,
    make_identifier_ref,
)

logger = logging.getLogger(__name__)

C = TypeVar("C", bound="Component")


class Component:
    """
    Conceptually, a Component is a graph node with edges and attributes, that
    can serialize itself to and from spec YAML strings and registries.

    A Component is the Python object version of a PCS Spec, which itself
    is a YAML dictionary that maps a content hash identifier string to
    its body. The body is, in turn, a map from str to attribute. Attributes
    can be type str, bool, None, number, dict, list, or Component.

    A value in the spec body map can be another Spec's identifier.
    This represents a causal dependency between the two Specs.
    """

    IDENTIFIER_KEY = "identifier"
    PRIVATE_IDENTIFIER_KEY = "_identifier"
    TYPE_KEY = "type"
    BODY_KEY = "body"
    PRIVATE_BODY_KEY = "_body"
    OK_LEAF_ATTR_TYPES = (numbers.Number, str, bool)

    def __init__(self):
        self._spec_attr_names: List[str] = []  # Updated by register_attribute.
        self._update_body()  # Initializes self._body and self._spec_body.
        self._update_identifier()  # Creates and initializes self._identifier.
        # A Component's identifier is not considered a spec_attribute. Rather,
        # it is a function of all spec_attributes.
        self.register_attribute(self.TYPE_KEY)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return NotImplemented

    def __str__(self) -> str:
        return self.identifier

    def __hash__(self) -> int:
        return int(self.sha1(), 16)

    # TODO: This should be moved to utils.py
    @staticmethod
    def spec_body_to_identifier(spec_body: Dict) -> str:
        return DeepHash(spec_body, hasher=DeepHash.sha1hex)[spec_body]

    def sha1(self) -> str:
        return self.spec_body_to_identifier(self._spec_body)

    def attribute_is_registered(self, attribute_name: str) -> bool:
        return attribute_name in self._spec_attr_names

    def register_attribute(self, attribute_name: str):
        assert attribute_name != self.IDENTIFIER_KEY, (
            f"{self.IDENTIFIER_KEY} cannot be registered as an "
            "attribute since it is a function of all attributes."
        )
        assert attribute_name != self.PRIVATE_IDENTIFIER_KEY, (
            f"{self.PRIVATE_IDENTIFIER_KEY} cannot be registered as an "
            "attribute since it is used internally by pcs.Component."
        )
        assert attribute_name != self.BODY_KEY, (
            f"{self.BODY_KEY} cannot be registered as an "
            "attribute since it is a function of all attributes."
        )
        assert attribute_name != self.PRIVATE_BODY_KEY, (
            f"{self.PRIVATE_BODY_KEY} cannot be registered as an "
            "attribute since it is used internally by pcs.Component."
        )
        assert attribute_name not in self._spec_attr_names
        assert hasattr(self, attribute_name), (
            f"{self.type} Component ({self}) does not have attribute "
            f"{attribute_name}"
        )
        self._spec_attr_names.append(attribute_name)
        self._update_body()
        self._update_identifier()

    def register_attributes(self, attribute_names: Collection[str]):
        for name in attribute_names:
            self.register_attribute(name)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if hasattr(self, "_spec_attr_names") and name in self._spec_attr_names:
            self._update_body()
            self._update_identifier()

    def copy(self):
        return self.from_registry(self.to_registry(), self.identifier)

    @property
    def type(self):
        return self.__class__.__name__

    @property
    def identifier(self) -> str:
        return self._identifier

    def _update_identifier(self):
        self._identifier = self.sha1()

    @property
    def body(self) -> Dict:
        return self._body

    def _update_body(self):
        self._body = {}
        for name in self._spec_attr_names:
            attr = {name: getattr(self, name, None)}

            def not_allowed(i):
                allowed = (
                    i is None
                    or isinstance(i, Component)
                    or isinstance(i, self.OK_LEAF_ATTR_TYPES)
                )
                return not allowed

            # Stringify all non-allowed types.
            _, attr = copy_find_and_replace_leaves(
                attr, not_allowed, lambda leaf: str(leaf)
            )
            self._body.update(attr)

        # Stringify dependencies for self._spec_body
        _, self._spec_body = copy_find_and_replace_leaves(
            self._body,
            lambda leaf: isinstance(leaf, Component),
            lambda leaf: make_identifier_ref(leaf.identifier),
        )

    def dependencies(self, filter_by_types: Sequence[Type[C]] = None) -> Dict:
        """
        Returns the subset of ``self.attributes`` that are references to
        other Components, optionally filtered to only those of any of the
        list of Component types provided in 'filter_by_types'.
        """

        def filter_fn(leaf):
            return isinstance(leaf, Component) and (
                not filter_by_types or type(leaf) in filter_by_types
            )

        return {
            k: v
            for k, v in filter_leaves(self.body, filter_fn=filter_fn).items()
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
        existing = registry.get_spec(
            self.identifier, error_if_not_found=False, flatten=False
        )
        # Test whether pushing this spec to registry will succeed.
        # NJTODO - sometimes existing is a dict, sometimes its a spec
        if existing:
            existing_is_dict = type(existing) is dict
            existing = existing if existing_is_dict else existing.to_dict()
            diff = DeepDiff(existing, self.to_spec().to_dict())
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
        dep_objs = self.dependencies().values()
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
        return cls.from_spec(registry.get_spec(identifier), registry)

    @classmethod
    def from_default_registry(cls, identifier: str) -> "Component":
        return cls.from_registry(Registry.from_default(), identifier)

    @classmethod
    def from_registry_file(
        cls,
        yaml_file: str,
        identifier: str,
    ) -> "Component":
        registry = Registry.from_yaml(yaml_file)
        return cls.from_registry(registry, identifier)

    def to_spec(self, flatten: bool = False) -> Dict:
        spec = Spec({self.identifier: self._spec_body})
        return flatten_spec(spec) if flatten else spec

    @classmethod
    def from_spec(cls, spec: Mapping, registry: Registry = None) -> Mapping:
        # TODO: assert if spec has dependencies then registry is not None
        resolved_deps = {}
        return cls._from_spec(spec, registry, resolved_deps)

    @classmethod
    def _from_spec(
        cls, spec: Mapping, registry: Registry, resolved_deps: Dict
    ) -> Mapping:
        spec = Spec(copy.deepcopy(spec))
        spec.replace_in_body(
            is_identifier_ref,
            lambda leaf: cls._resolve_dep(
                extract_identifier(leaf), registry, resolved_deps
            ),
        )
        assert hasattr(pcs, spec.type), (
            f"No Component type '{spec.type}' found in " "module 'pcs'. "
            "You may need to add it to pcs/__init__.py."
        )
        comp_cls = getattr(pcs, spec.type)
        logger.debug(f"creating cls {comp_cls} with kwargs {spec.as_kwargs}")
        try:
            comp_class = comp_cls(**spec.as_kwargs)
        except Exception as e:
            raise Exception(
                f"failed to initialize Component class {comp_cls} "
                f"with kwargs: {spec.as_kwargs}"
            ) from e
        return comp_class

    @classmethod
    def _resolve_dep(
        cls, identifier: str, registry: Registry, resolved_deps: Dict
    ):
        if identifier in resolved_deps:
            return resolved_deps[identifier]
        assert registry, (
            f"{cls.__name__} requires a registry to be "
            "passed in order to create a Component from the provided "
            "spec that has dependencies."
        )
        dep_spec = registry.get_spec(identifier, flatten=True)
        assert hasattr(pcs, dep_spec[cls.TYPE_KEY]), (
            f"Cannot find pcs.{dep_spec[cls.TYPE_KEY]}."
        )
        dep_comp_cls = getattr(pcs, dep_spec[cls.TYPE_KEY])
        assert issubclass(dep_comp_cls, Component)
        dep = dep_comp_cls._from_spec(
            unflatten_spec(dep_spec), registry, resolved_deps
        )
        assert identifier not in resolved_deps
        resolved_deps[identifier] = dep
        return dep

    @classmethod
    def from_yaml_str(cls, yaml_str: str):
        return cls(yaml.load(yaml_str))

    @classmethod
    def from_yaml_file(cls, filename: str):
        with open(filename) as f:
            return cls(yaml.load(f))

    def to_yaml_str(self) -> str:
        return yaml.dump(self.to_spec())

    def to_yaml_file(self, filename: str) -> None:
        self.to_registry().to_yaml(filename)

    def publish(self) -> Registry:
        self.to_registry(Registry.from_default())

    def dependency_list(
        self,
        include_root: bool = True,
        include_parents: bool = False,
        filter_by_types: Sequence[Type[C]] = None,
    ) -> Sequence["Component"]:
        """
        Return a normalized (i.e. flat) Sequence containing all transitive
        dependencies of this component and (optionally) this component.

        :param include_root: Whether to include root component in the list.
            If True, self is included in the list returned.
        :param include_parents: If True, then recursively include all parents
            of this component (and their parents, etc). A parent of this
            Component is a Component which depends on this. Ultimately,
            if True, all Components in the DAG will be returned.
        :param filter_by_types: list of classes whose type is 'type'.

        :return: a list containing all all of the transitive dependencies
                 of this component (optionally  including the root component).
        """
        module_queue = [self]
        ret_val = set()
        while module_queue:
            module = module_queue.pop()
            if include_root or module is not self:
                ret_val.add(module)
            for dependency in module.dependencies(
                filter_by_types=filter_by_types
            ).values():
                if dependency not in ret_val:
                    module_queue.append(dependency)
            if include_parents and hasattr(module, "_parent_modules"):
                for parent in module._parent_modules:
                    if parent not in ret_val:
                        module_queue.append(parent)
        return list(ret_val)

    def print_status_tree(self) -> None:
        tree = self.get_status_tree()
        rich_print(tree)

    def get_status_tree(self, parent_tree: Tree = None) -> Tree:
        self_tree = Tree(f"{self.type}: {self.identifier}")
        if parent_tree is not None:
            parent_tree.add(self_tree)
        for dep_attr_name, dep_module in self.dependencies().items():
            dep_module.get_status_tree(parent_tree=self_tree)
        return self_tree
