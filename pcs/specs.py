"""
Specs are always mappings. By default, specs map from an identifier string to
a mapping of key-value properties of the spec

For developer convenience many functions support flattened specs, which have
the spec identifier at the same level as the rest of the spec properties.
"""

import copy
from collections import UserDict
from typing import Callable, Dict, Mapping
from pcs.utils import find_and_replace_leaves


class Spec(UserDict):
    """
    A Specs is a Mapping of the form::

        {
            identifier:
                {
                    type: some_type_here
                    <optional other key->val attributes>
                }
        }

    A spec is always a nested dict, i.e.: a dict inside a dict.
    The inner dict is called the 'body'. There must be
    exactly one key in the outer dict: the identifier of the spec, which
    is a hash of the inner dict.

    Any Spec can also be represented as a flat dict, of the form::

        {identifier: <str>, type: <str>, <other key->val flat_spec>}
    """
    def __init__(self, input_dict: Dict):
        self.data = input_dict
        self._check_format()

    @property
    def identifier(self):
        self._check_format()
        for ident, body in self.data.items():
            return ident
        raise Exception(f"{self} is a malformed")

    @property
    def body(self):
        self._check_format()
        for ident, body in self.data.items():
            return body

    @property
    def type(self) -> str:
        from pcs.component import Component  # Avoid circular import.

        return self.body[Component.TYPE_KEY]

    @property
    def as_kwargs(self):
        return {k: v for k, v in self.body.items() if k != "type"}

    def _check_format(self):
        assert len(self.data) == 1, (
            f"len(self.data) must be 1, but is {len(self.data)}. self.data "
            f"is:\n{self.data}"
        )
        from pcs.component import Component  # Avoid circular import.

        for ident, body in self.data.items():
            assert Component.spec_body_to_identifier(body) == ident, (
                f"{Component.spec_body_to_identifier(body)} != {ident}.\n"
                f"body is:\n{body}"
            )

    def _update_identifier(self):
        from pcs.component import Component  # Avoid circular import.

        for ident, body in self.data.items():
            self.data = {Component.spec_body_to_identifier(body): body}
        self._check_format()

    def update_body(self, update_dict: Dict) -> None:
        self.data[self.identifier].update(update_dict)
        self._update_identifier()

    def replace_in_body(
            self, filter_fn: Callable, replace_fn: Callable
    ) -> bool:
        found = find_and_replace_leaves(self.body, filter_fn, replace_fn)
        self._update_identifier()
        return found

    @classmethod
    def from_flat(cls, flat_spec: Dict) -> "Spec":
        from pcs.component import Component  # Avoid circular import.

        assert Component.TYPE_KEY in flat_spec
        ident_computed = Component.spec_body_to_identifier(flat_spec)
        flat_spec_copy = copy.deepcopy(flat_spec)
        if Component.IDENTIFIER_KEY in flat_spec:
            ident_in = flat_spec_copy.pop(Component.IDENTIFIER_KEY)
            assert ident_computed == ident_in, (
                "The identifier in the provided dict does not match the "
                "hash of the other contents (i.e. the attributes) of the "
                "dict provided."
            )
        return cls({ident_computed: flat_spec_copy})

    def to_flat(self):
        return flatten_spec(self.data)


def flatten_spec(nested_spec: Mapping) -> Mapping:
    assert (
        len(nested_spec.keys()) == 1
    ), f"Only specs w/ one key can be flattened: {nested_spec}"
    flat_spec = {}
    for identifier, inner_spec in nested_spec.items():
        assert type(identifier) == str
        from pcs.component import Component  # Avoid circular import.

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
    from pcs.component import Component  # Avoid circular import.

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
    from pcs.component import Component  # Avoid circular import.

    return Component.IDENTIFIER_KEY in spec
