import copy
import yaml
from typing import TypeVar, Dict
from agentos.specs import ParameterSetSpec

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ParameterSet:
    """
    This object is used to encapsulate a set of parameters that are used to
    initialize a Component dependency DAG and to run methods on this DAG.
    """

    def __init__(self, parameters: ParameterSetSpec = None):
        self.parameters = parameters if parameters else {}

    @classmethod
    def get_from_yaml(cls, file_path) -> "ParameterSet":
        parameters = {}
        if file_path is not None:
            with open(file_path) as file_in:
                parameters = yaml.safe_load(file_in)
        return ParameterSet(parameters=parameters)

    def update(self, component_name: str, fn_name: str, params: Dict) -> None:
        component_params = self.parameters.get(component_name, {})
        fn_params = component_params.get(fn_name, {})
        fn_params.update(params)
        component_params[fn_name] = fn_params
        self.parameters[component_name] = component_params

    def get(self, component_name: str, fn_name: str):
        component_params = self.parameters.get(component_name, {})
        fn_params = component_params.get(fn_name, {})
        return fn_params if fn_params else {}

    def to_spec(self) -> ParameterSetSpec:
        return copy.deepcopy(self.parameters)
