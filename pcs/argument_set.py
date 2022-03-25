import copy
import json
from hashlib import sha1
from typing import Dict, Mapping, TypeVar

import yaml

from pcs.specs import ArgumentSetSpec

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ArgumentSet:
    """
    This object is used to encapsulate a set of arguments that are used to
    initialize a Component dependency DAG and to run methods on this DAG.
    """

    def __init__(self, arguments: Dict = None):
        if arguments:
            for component_name, fn_map in arguments.items():
                assert isinstance(component_name, str)
                assert isinstance(fn_map, Mapping)
                for fn_name, arg_map in fn_map.items():
                    assert isinstance(fn_name, str)
                    assert isinstance(arg_map, Mapping)
                    for arg_name, arg_val in arg_map.items():
                        assert isinstance(arg_name, str)
        self._arguments = arguments if arguments else {}
        # Ensure serializability.
        assert self.to_sorted_dict_str(), "arguments dict must be serializable"

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(self)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return int(self._sha1(), 16)

    def __str__(self) -> str:
        return self.identifier

    @property
    def identifier(self) -> str:
        return self._sha1()

    @classmethod
    def from_yaml(cls, file_path) -> "ArgumentSet":
        arguments = {}
        if file_path is not None:
            with open(file_path) as file_in:
                arguments = yaml.safe_load(file_in)
        return ArgumentSet(arguments)

    @classmethod
    def from_spec(cls, arg_set_spec: ArgumentSetSpec) -> "ArgumentSet":
        assert (
            len(arg_set_spec) == 1
        ), "arg_set_spec must be a dict with a single key-value pair"
        arg_set_spec_id, inner_arg_set = None, {}
        for key, value in arg_set_spec.items():
            arg_set_spec_id = key
            inner_arg_set = value
        new_arg_set = cls(inner_arg_set)
        assert new_arg_set.identifier == arg_set_spec_id, (
            "Since arg_set_id is a hash of the arg_set contents, the "
            f"identifier of the new arg_set {new_arg_set.identifier} "
            "should match the identifier of the spec it was loaded from "
            f"{arg_set_spec_id}, but the two ids don't match."
        )
        return new_arg_set

    def update(self, component_name: str, fn_name: str, args: Dict) -> None:
        component_args = self._arguments.get(component_name, {})
        fn_args = component_args.get(fn_name, {})
        fn_args.update(args)
        component_args[fn_name] = fn_args
        self._arguments[component_name] = component_args

    def get_component_args(self, component_name: str) -> Dict:
        return self._arguments.get(component_name, {})

    def get_function_args(
        self, component_name: str, function_name: str
    ) -> Dict:
        component_args = self.get_component_args(component_name)
        fn_args = component_args.get(function_name, {})
        return fn_args if fn_args else {}

    def get_arg(
        self, component_name: str, function_name: str, arg_key: str
    ) -> Dict:
        fn_args = self.get_function_args(component_name, function_name)
        arg = fn_args.get(arg_key, {})
        return arg if arg else {}

    def to_spec(self, flatten: bool = False) -> ArgumentSetSpec:
        inner = copy.deepcopy(self._arguments)
        if flatten:
            inner.update({ArgumentSetSpec.identifier_key: self.identifier})
            return inner
        else:
            return {str(self.identifier): inner}

    def _sha1(self) -> str:
        # Not positive if this is stable across architectures.
        # See https://stackoverflow.com/q/27522626
        return sha1(self.to_sorted_dict_str().encode("utf-8")).hexdigest()

    def to_sorted_dict_str(self) -> str:
        # See https://stackoverflow.com/a/22003440
        return json.dumps(self._arguments, sort_keys=True)
