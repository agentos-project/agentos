from typing import Dict, Union

FlatComponentSpec = Dict[str, str]
NestedComponentSpec = Dict[str, Dict[str, str]]
ComponentSpec = Union[NestedComponentSpec, FlatComponentSpec]

# Repo is serialized to a dictionary with the following form:
# {"repo_name": { repo_property_key: repo_property_val}
RepoSpec = Dict[str, Dict[str, str]]

# A paramSet is serialized as a ParameterSetSpec, which is a dictionary
# with the following structure:
# {class_name: {entry_point_name: {param_name: param_val}}
ParameterSetSpec = Dict[str, Dict[str, Dict[str, str]]]
