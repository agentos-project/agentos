import copy
import logging
import numbers
from rich import print as rich_print
from rich.tree import Tree
from typing import (
    Collection,
    Dict,
    List,
    Mapping,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    TYPE_CHECKING
)
import yaml
from deepdiff import DeepDiff, DeepHash, grep

import pcs  # for hasattr(pcs, ...)
from pcs.registry import InMemoryRegistry, Registry
from pcs.specs import flatten_spec, unflatten_spec
from pcs.utils import (
    IDENTIFIER_REGEXES, is_identifier, find_and_replace_leaves
)

if TYPE_CHECKING:
    from pcs.component import Module

logger = logging.getLogger(__name__)

C = TypeVar('C', bound='Component')


class Component:
    """
    A Component is a Python class whose instances can serialize themselves
    to and from spec YAML strings and registry objects.

    A Component is the Python object version of a PCS Spec, which itself
    is a YAML dictionary that maps a content hash identifier string to
    "spec contents". The contents of a spec are, in turn, a str->str map.

    A value in the spec contents map can be another Spec's identifier.
    This represents a causal dependency between the two Specs.
    """

    IDENTIFIER_KEY = "identifier"
    TYPE_KEY = "type"
    OK_LEAF_ATTR_TYPES = (numbers.Number, str, bool)

    def __init__(self):
        self._identifier = ""  # Is updated by self.register_attributes()
        self._spec_attr_names: List[str] = []  # Managed by register_attribute
        # A Component's identifier is not considered a spec_attribute. # Rather,
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

    @staticmethod
    def spec_body_to_identifier(spec_body: Dict) -> str:
        return DeepHash(spec_body, hasher=DeepHash.sha1hex)[spec_body]

    def sha1(self) -> str:
        body = self.body(dependencies_as_strings=True)
        return self.spec_body_to_identifier(body)

    def register_attribute(self, attribute_name: str):
        assert attribute_name != self.IDENTIFIER_KEY, (
            f"{self.IDENTIFIER_KEY} cannot be registered as an "
            "attribute since it is a function of all attributes."
        )
        assert attribute_name not in self._spec_attr_names
        assert hasattr(self, attribute_name), (
            f"{self.type} Component ({self}) does not have attribute "
            f"{attribute_name}"
        )
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
        return self._identifier

    def body(self, dependencies_as_strings=False) -> Dict:
        attributes = {}
        for name in self._spec_attr_names:
            attr = {name: copy.deepcopy(getattr(self, name, None))}

            def not_allowed(i):
                allowed = (
                    isinstance(i, Component) or
                    isinstance(i, self.OK_LEAF_ATTR_TYPES)
                )
                return not allowed
            # Stringify all non-allowed types.
            find_and_replace_leaves(attr, not_allowed, lambda leaf: str(leaf))
            # Per 'dependencies_as_strings' flag, stringify dependencies
            if dependencies_as_strings:
                find_and_replace_leaves(
                    attr,
                    lambda leaf: isinstance(leaf, Component),
                    lambda leaf: leaf.identifier
                )
            attributes.update(attr)
        return attributes

    def dependencies(self, filter_by_types: Sequence[Type[C]] = None) -> Dict:
        """
        Returns the subset of ``self.attributes`` that are references to
        other Components, optionally filtered to only those of any of the
        list of Component types provided in 'filter_by_types'.
        """
        deps = {}
        for name, value in self.body().items():
            if isinstance(value, Component):
                if not filter_by_types or type(value) in filter_by_types:
                    deps.update({name: value})
        return deps

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
    def from_default_registry(cls, identifier: str) -> "Module":
        return cls.from_registry(Registry.from_default(), identifier)

    @classmethod
    def from_registry_file(
        cls,
        yaml_file: str,
        identifier: str,
    ) -> "Module":
        registry = Registry.from_yaml(yaml_file)
        return cls.from_registry(registry, identifier)

    def to_spec(self, flatten: bool = False) -> Dict:
        spec = {self.identifier: self.body(dependencies_as_strings=True)}
        return flatten_spec(spec) if flatten else spec

    @classmethod
    def from_spec(cls, spec: Mapping, registry: Registry = None) -> Mapping:
        flat_spec = flatten_spec(spec)
        kwargs = {}
        for k, v in flat_spec.items():
            # get instances of any dependencies in this spec.
            if k == cls.IDENTIFIER_KEY or k == cls.TYPE_KEY:
                continue
            if v and is_identifier(v):
                kwargs[k] = cls._resolve_dep_class(v, registry)
            elif isinstance(v, List) or isinstance(v, Tuple) or isinstance(v, Dict):
                for rx in IDENTIFIER_REGEXES:
                    root = v  # Necessary for the exec magic below.
                    results = v | grep(
                        rx, use_regexp=True, verbose_level=2
                    )
                    if results:
                        items = results['matched_values'].items()
                        for dict_as_str, ident in items:
                            # This is ugly and maybe unsafe and should be
                            # done in a more sane way.
                            assert isinstance(ident, str)
                            exec(
                                f"{dict_as_str} = "
                                "cls._resolve_dep_class(ident, registry)"
                            )
                        break
                kwargs[k] = root
            else:
                kwargs[k] = v

        assert hasattr(pcs, flat_spec[cls.TYPE_KEY]), (
            f"No Component type '{flat_spec[cls.TYPE_KEY]}' found in "
            "module 'pcs'."
        )
        comp_cls = getattr(pcs, flat_spec[cls.TYPE_KEY])
        print(f"creating cls {comp_cls} with kwargs {kwargs}")
        comp_class = comp_cls(**kwargs)
        return comp_class

    @classmethod
    def _resolve_dep_class(cls, identifier: str, registry: Registry):
        assert registry, (
            f"{cls.__name__} requires a registry to be "
            "passed in order to create a Component from the provided "
            "spec that has dependencies."
        )
        dep_spec = flatten_spec(registry.get_spec(identifier))
        assert hasattr(pcs, dep_spec[cls.TYPE_KEY])
        dep_comp_cls = getattr(pcs, dep_spec[cls.TYPE_KEY])
        assert issubclass(dep_comp_cls, Component)
        return dep_comp_cls.from_spec(
            unflatten_spec(dep_spec), registry=registry
        )

    @classmethod
    def from_yaml_str(cls, yaml_str: str):
        return cls(yaml.load(yaml_str))

    @classmethod
    def from_yaml_file(cls, filename: str):
        with open(filename, "r") as f:
            return cls(yaml.load(f))

    def to_yaml_str(self) -> str:
        return yaml.dump(self.to_spec())

    def to_yaml_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            yaml.dump(self.to_spec(), f)
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
            of this component (and their parents, etc). A parent of this Module
            is a Module which depends on this Module.  Ultimately, if True, all
            Components in the DAG will be returned.
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
        self_tree = Tree(f"Module: {self.identifier}")
        if parent_tree is not None:
            parent_tree.add(self_tree)
        for dep_attr_name, dep_module in self.dependencies().items():
            dep_module.get_status_tree(parent_tree=self_tree)
        return self_tree



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

        def __init__(
            self, repo: GitHubComponent, version: str, module_path: str
        ):
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
