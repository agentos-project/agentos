"""
The spec types in this file specify which types of objects can be added to a
Registry. They are literally types, and used in type annotations on core
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


FlatSpec = Mapping[str, str]


NestedComponentSpec = Mapping[str, Mapping[str, str]]
ComponentSpec = Union[NestedComponentSpec, FlatSpec]


class VersionedSpec:
    SEPARATOR = "=="


class ComponentSpecKeys:
    IDENTIFIER = "identifier"
    NAME = "name"
    VERSION = "version"
    CLASS_NAME = "class_name"
    FILE_PATH = "file_path"
    DEPENDENCIES = "dependencies"


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
    COMPONENT_ID = "component"
    ENTRY_POINT = "entry_point"
    PARAMETER_SET = "parameter_set"


RunSpec = Mapping


class RunSpecKeys:
    IDENTIFIER = "identifier"


def flatten_spec(nested_spec: dict) -> dict:
    assert len(nested_spec.keys()) == 1
    flat_spec = {}
    for identifier, inner_spec in nested_spec.items():
        assert type(identifier) == str
        flat_spec.update(copy.deepcopy(inner_spec))
        for key_check in [
            ComponentSpecKeys.IDENTIFIER,
            ComponentSpecKeys.NAME,
            ComponentSpecKeys.VERSION,
        ]:
            assert key_check not in flat_spec, (
                f"'{key_check}' is a reserved key: it cannot be "
                "set by a developer since PCS sets it automatically when "
                "flattening specs."
            )
        flat_spec[ComponentSpecKeys.IDENTIFIER] = identifier
        id_parts = identifier.split(VersionedSpec.SEPARATOR)
        assert 0 < len(id_parts) <= 2, f"invalid identifier {identifier}"
        flat_spec[ComponentSpecKeys.NAME] = id_parts[0]
        if len(id_parts) == 2:
            flat_spec[ComponentSpecKeys.VERSION] = id_parts[1]
        else:
            flat_spec[ComponentSpecKeys.VERSION] = None
    return flat_spec


def unflatten_spec(flat_spec: object) -> object:
    assert ComponentSpecKeys.IDENTIFIER in flat_spec
    if VersionedSpec.SEPARATOR in flat_spec[ComponentSpecKeys.IDENTIFIER]:
        identifier = flat_spec[ComponentSpecKeys.IDENTIFIER]
        parts = identifier.split(VersionedSpec.SEPARATOR)
        assert len(parts) == 2
        for check_key in [ComponentSpecKeys.NAME, ComponentSpecKeys.VERSION]:
            assert check_key in flat_spec, (
                f"'{check_key} must be a key in a flat spec that "
                "has a versioned identifier (i.e., that has an '==' in its "
                "identifier."
            )
    dup_spec = copy.deepcopy(flat_spec)
    return {dup_spec.pop(ComponentSpecKeys.IDENTIFIER): dup_spec}
