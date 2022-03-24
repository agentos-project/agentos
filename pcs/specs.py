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
ArgumentSetSpec, those values can themselves be mappings.

For developer convenience many functions support flattened specs, which have
the spec identifier at the same level as the rest of the spec properties.
"""

import copy
import json
from typing import Any, Mapping, Union

from pcs.identifiers import ComponentIdentifier

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


# A arg_set is serialized as a ArgumentSetSpec, which is a YAML dictionary
# with the following structure:
# {component_name: {entry_point_name: {arg_name: arg_val}}
#
# arg_value can be any type supported by YAML, which includes:
# scalars (numeric or string), potentially nested lists or dictionaries with
# scalars as leaf values.
#
# Note that you can have a run use complex types via the dependencies
# mechanism which allows a component to depend on other components,
# which themselves can be instances of an arbitrary Python class.
# TODO: Figure out a better type than Any for the leaf type here.
#       Specifically, one that captures the required serializability.
ArgumentSetSpec = Mapping[str, Mapping[str, Mapping[str, Any]]]
ArgumentSetSpec.identifier_key = "identifier"


RunCommandSpec = Mapping


class RunCommandSpecKeys:
    IDENTIFIER = "identifier"  # for flattened RunCommandSpec
    COMPONENT_ID = "component"
    ENTRY_POINT = "entry_point"
    ARGUMENT_SET = "argument_set"
    LOG_RETURN_VALUE = "log_return_value"


RunSpec = Mapping


class RunSpecKeys:
    IDENTIFIER = "identifier"


def flatten_spec(nested_spec: Mapping) -> Mapping:
    assert (
        len(nested_spec.keys()) == 1
    ), f"Only specs w/ one key can be flattened: {nested_spec}"
    flat_spec = {}
    for identifier, inner_spec in nested_spec.items():
        assert type(identifier) == str
        flat_spec.update(copy.deepcopy(inner_spec))

        def err(attr):
            return (
                f"'{attr}' is a reserved spec key: if it exists inside a "
                "nested spec, its value must match the spec's identifier."
            )

        if ComponentSpecKeys.IDENTIFIER in flat_spec:
            flat_spec_id = flat_spec[ComponentSpecKeys.IDENTIFIER]
            assert flat_spec_id == identifier, err("identifier")
        if ComponentSpecKeys.NAME in flat_spec:
            name = ComponentIdentifier(identifier).name
            assert flat_spec[ComponentSpecKeys.NAME] == name, err("name")
        if ComponentSpecKeys.VERSION in flat_spec:
            ver = ComponentIdentifier(identifier).version
            assert flat_spec[ComponentSpecKeys.version] == ver, err("version")
        flat_spec[ComponentSpecKeys.IDENTIFIER] = identifier
        id_parts = identifier.split(VersionedSpec.SEPARATOR)
        assert 0 < len(id_parts) <= 2, f"invalid identifier {identifier}"
        flat_spec[ComponentSpecKeys.NAME] = id_parts[0]
        if len(id_parts) == 2:
            flat_spec[ComponentSpecKeys.VERSION] = id_parts[1]
        else:
            flat_spec[ComponentSpecKeys.VERSION] = None
    return flat_spec


def unflatten_spec(
    flat_spec: Mapping, preserve_inner_identifier: bool = False
) -> Mapping:
    """
    Takes a flat spec, and returns a nested spec. A nested spec is a map
    from the spec's identifier to a map of the specs other key->value
    attributes. A flat spec moves the identifier into the inner map,
    essentially flattening the outer two dictionaries into a single dictionary.

    :param flat_spec: a flat spec to unflatten.
    :param preserve_inner_identifier: if true, do not delete 'identiifer',
        'name', or 'version' keys (and their associated values) from the inner
        part of the nested spec that is returned. Else, do remove them, i.e.,
        normalize the spec.
    :return: Nested version of ``flat_spec``.
    """
    assert ComponentSpecKeys.IDENTIFIER in flat_spec
    identifier = flat_spec[ComponentSpecKeys.IDENTIFIER]
    if VersionedSpec.SEPARATOR in identifier:
        parts = identifier.split(VersionedSpec.SEPARATOR)
        assert len(parts) == 2
        for check_key in [ComponentSpecKeys.NAME, ComponentSpecKeys.VERSION]:
            assert check_key in flat_spec, (
                f"'{check_key} must be a key in a flat spec that "
                "has a versioned identifier (i.e., that has an '==' in its "
                "identifier."
            )
    dup_spec = copy.deepcopy(flat_spec)
    if not preserve_inner_identifier:
        if ComponentSpecKeys.NAME in dup_spec:
            dup_spec.pop(ComponentSpecKeys.NAME)
        if ComponentSpecKeys.VERSION in dup_spec:
            dup_spec.pop(ComponentSpecKeys.VERSION)
        if ComponentSpecKeys.IDENTIFIER in dup_spec:
            dup_spec.pop(ComponentSpecKeys.IDENTIFIER)
    return {identifier: dup_spec}


def is_flat(spec: Mapping) -> bool:
    assert len(spec) > 0  # specs must have at least one key-value pair.
    # Nested specs have exactly one outer-most key, i.e., their identifier.
    # Flat specs have more than one (the identifier and something else).
    return not len(spec) == 1


def json_encode_flat_spec_field(spec: Mapping, field_name: str) -> Mapping:
    assert is_flat(spec)
    assert field_name in spec, f"no key '{field_name}' in spec '{spec}'."
    spec_copy = copy.deepcopy(spec)
    spec_copy[field_name] = json.encoder.JSONEncoder().encode(
        spec_copy[field_name]
    )
    return spec_copy
