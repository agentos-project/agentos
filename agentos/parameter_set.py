import copy
import yaml
import json
from hashlib import sha1
from typing import TypeVar, Mapping, Dict
from agentos.specs import ParameterSetSpec

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ParameterSet:
    """
    This object is used to encapsulate a set of parameters that are used to
    initialize a Component dependency DAG and to run methods on this DAG.
    """

    def __init__(self, parameters: Dict = None):
        if parameters:
            for component_name, fn_map in parameters.items():
                assert isinstance(component_name, str)
                assert isinstance(fn_map, Mapping)
                for fn_name, param_map in fn_map.items():
                    assert isinstance(fn_name, str)
                    assert isinstance(param_map, Mapping)
                    for param_name, param_val in param_map.items():
                        assert isinstance(param_name, str)
        self._parameters = parameters if parameters else {}
        # Ensure serializability.
        assert (
            self.to_sorted_dict_str()
        ), "parameters dict must be serializable"

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
    def from_yaml(cls, file_path) -> "ParameterSet":
        parameters = {}
        if file_path is not None:
            with open(file_path) as file_in:
                parameters = yaml.safe_load(file_in)
        return ParameterSet(parameters=parameters)

    @classmethod
    def from_spec(cls, param_set_spec: ParameterSetSpec) -> "ParameterSet":
        assert (
            len(param_set_spec) == 1
        ), "param_set_spec must be a dict with a single key-value pair"
        param_set_spec_id, inner_param_set = None, None
        for key, value in param_set_spec.items():
            param_set_spec_id = key
            inner_param_set = value
        new_param_set = cls(inner_param_set)
        assert new_param_set.identifier == param_set_spec_id, (
            "Since param_set_id is a hash of the param_set contents, the "
            f"identifier of the new param_set {new_param_set.identifier} "
            "should match the identifier of the spec it was loaded from "
            f"{param_set_spec_id}, but the two ids don't match."
        )
        return new_param_set

    def update(self, component_name: str, fn_name: str, params: Dict) -> None:
        component_params = self._parameters.get(component_name, {})
        fn_params = component_params.get(fn_name, {})
        fn_params.update(params)
        component_params[fn_name] = fn_params
        self._parameters[component_name] = component_params

    def get_component_params(self, component_name: str) -> Dict:
        return self._parameters.get(component_name, {})

    def get_function_params(
        self, component_name: str, function_name: str
    ) -> Dict:
        component_params = self.get_component_params(component_name)
        fn_params = component_params.get(function_name, {})
        return fn_params if fn_params else {}

    def get_param(
        self, component_name: str, function_name: str, param_key: str
    ) -> Dict:
        fn_params = self.get_function_params(component_name, function_name)
        param = fn_params.get(param_key, {})
        return param if param else {}

    def to_spec(self, flatten: bool = False) -> ParameterSetSpec:
        inner = copy.deepcopy(self._parameters)
        if flatten:
            inner.update({ParameterSetSpec.identifier_key: self.identifier})
            return inner
        else:
            return {str(self.identifier): inner}

    def _sha1(self) -> str:
        # Not positive if this is stable across architectures.
        # See https://stackoverflow.com/q/27522626
        return sha1(self.to_sorted_dict_str().encode("utf-8")).hexdigest()

    def to_sorted_dict_str(self) -> str:
        # See https://stackoverflow.com/a/22003440
        return json.dumps(self._parameters, sort_keys=True)
