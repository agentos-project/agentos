"""
The Specs Types in this file specify which types of objects that can be added
to a Registry. They are literally types, and used in type annotions on core
abstractions.

Though this isn't currently enforced by the types, objects that are Specs
should be serializable to YAML format and are human readable and manageable.

Currently dicts are most often used where a Spec is required by type
signatures.

Specs are always mappings. By default, specs map from an identifier string to
a mapping of key-value properties of the spec; and in some specs such as
ParameterSetSpec, those values can themselves be mappings.

For developer convenience many functions support flattened specs, which have
the spec identifier at the same level as the rest of the spec properties.
"""

from typing import Mapping, Union, Any
import copy


def flatten_spec(nested_spec: dict) -> dict:
    assert len(nested_spec.keys()) == 1
    flat_spec = {}
    for identifier, inner_spec in nested_spec.items():
        assert type(identifier) == str
        flat_spec.update(copy.deepcopy(inner_spec))
        assert "identifier" not in flat_spec
        flat_spec["identifier"] = identifier
        if "==" in identifier:
            assert "name" not in flat_spec, (
                "'name' cannot be a key in a nested spec that has a '==' "
                "in its identifier."
            )
            assert "version" not in flat_spec, (
                "'version' cannot be a key in a nested spec that has a '==' "
                "in its identifier."
            )
            parts = identifier.split("==")
            assert len(parts) == 2
            flat_spec["name"], flat_spec["version"] = parts
    return flat_spec


def unflatten_spec(flat_spec: dict) -> dict:
    assert "identifier" in flat_spec
    if "==" in flat_spec["identifier"]:
        parts = flat_spec["identifier"].split("==")
        assert len(parts) == 2
        assert "name" in flat_spec, (
            "'name' must be a key in a flat spec with a versioned identifier"
        )
        assert "version" in flat_spec, (
            "'version' must be a key in a flat spec that has a versioned "
            "identifier (i.e., that has an '==' in its identifier."
        )
    dup_spec = copy.deepcopy(flat_spec)
    return {dup_spec.pop("identifier"): dup_spec}


FlatSpec = Mapping[str, str]


NestedComponentSpec = Mapping[str, Mapping[str, str]]
ComponentSpec = Union[NestedComponentSpec, FlatSpec]


class ComponentSpecKeys:
    IDENTIFIER = "identifier"


# Repo is serialized to a YAML dictionary with the following (unflatted) form:
# {repo_identifier: {repo_property_key: repo_property_val}}
NestedRepoSpec = Mapping[str, Mapping[str, str]]
RepoSpec = Union[NestedRepoSpec, FlatSpec]


class RepoSpecKeys:
    IDENTIFIER = "identifier"
    TYPE = "type"
    URL = "url"
    PATH = "path"


# A paramSet is serialized as a ParameterSetSpec, which is a YAML dictionary
# with the following structure:
# {component_name: {entry_point_name: {param_name: param_val}}
#
# param_value can be any type supported by YAML, which includes:
# scalars (numeric or string), potentially nested lists or dictionaries with
# scalars as leaf values.
#
# Note that you can have a run use complex types via the dependencies
# mechanism which allows a component to depend on other components,
# which themselves can be instances of an arbitrary Python class.
# TODO: Figure out a better type than Any for the leaf type here.
#       Specifically, one that captures the required serializability.
ParameterSetSpec = Mapping[str, Mapping[str, Mapping[str, Any]]]
ParameterSetSpec.identifier_key = "identifier"


RunCommandSpec = Mapping


class RunCommandSpecKeys:
    IDENTIFIER = "identifier"  # for flattened RunCommandSpec
    COMPONENT_ID = "component_id"
    ENTRY_POINT = "entry_point"
    PARAMETER_SET = "parameter_set"


RunSpec = Mapping


class RunSpecKeys:
    IDENTIFIER = "identifier"
