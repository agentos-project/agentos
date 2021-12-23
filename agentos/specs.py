from typing import Mapping, Union

FlatComponentSpec = Mapping[str, str]
NestedComponentSpec = Mapping[str, Mapping[str, str]]
ComponentSpec = Union[NestedComponentSpec, FlatComponentSpec]

# Repo is serialized to a dictionary with the following form:
# {"repo_name": { repo_property_key: repo_property_val}
RepoSpec = Mapping[str, Mapping[str, str]]

# A paramSet is serialized as a ParameterSetSpec, which is a dictionary
# with the following structure:
# {class_name: {entry_point_name: {param_name: param_val}}
ParameterSetSpec = Mapping[str, Mapping[str, Mapping[str, str]]]
