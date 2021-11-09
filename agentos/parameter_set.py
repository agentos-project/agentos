import copy
import yaml
from typing import TypeVar, Dict

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ParameterSet:
    def __init__(self, parameters: Dict = None):
        self.parameters = parameters if parameters else {}

    @classmethod
    def get_from_file(cls, file_path) -> "ParameterSet":
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
        return component_params.get(fn_name, {})

    def to_dict(self):
        return copy.deepcopy(self.parameters)
