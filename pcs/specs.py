"""
Specs are always mappings. By default, specs map from an identifier string to
a mapping of key-value properties of the spec

For developer convenience many functions support flattened specs, which have
the spec identifier at the same level as the rest of the spec properties.
"""

import copy
from typing import Mapping


def flatten_spec(nested_spec: Mapping) -> Mapping:
    assert (
        len(nested_spec.keys()) == 1
    ), f"Only specs w/ one key can be flattened: {nested_spec}"
    flat_spec = {}
    for identifier, inner_spec in nested_spec.items():
        assert type(identifier) == str
        from pcs.spec_object import Component  # Avoid circular import.

        flat_spec[Component.IDENTIFIER_KEY] = identifier
        flat_spec.update(copy.deepcopy(inner_spec))
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
    :param preserve_inner_identifier: if true, do not delete 'identifier',
        'name', or 'version' keys (and their associated values) from the inner
        part of the nested spec that is returned. Else, do remove them, i.e.,
        normalize the spec.
    :return: Nested version of ``flat_spec``.
    """
    from pcs.spec_object import Component  # Avoid circular import.

    assert Component.IDENTIFIER_KEY in flat_spec
    identifier = flat_spec[Component.IDENTIFIER_KEY]
    dup_spec = copy.deepcopy(flat_spec)
    if not preserve_inner_identifier:
        if Component.IDENTIFIER_KEY in dup_spec:
            dup_spec.pop(Component.IDENTIFIER_KEY)
    return {identifier: dup_spec}


def is_flat_spec(spec: Mapping) -> bool:
    assert len(spec) > 0  # specs must have at least one key-value pair.
    # Flat specs must have an identifier in their outermost dict.
    from pcs.spec_object import Component  # Avoid circular import.

    return Component.IDENTIFIER_KEY in spec
