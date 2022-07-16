"""
Specs are always mappings. By default, specs map from an identifier string to
a mapping of key-value properties of the spec

For developer convenience many functions support flattened specs, which have
the spec identifier at the same level as the rest of the spec properties.
"""

import copy
from collections import UserDict
from typing import Callable, Dict, Mapping

from pcs.utils import extract_identifier, find_and_replace_leaves, is_spec_body


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

    def __init__(self, input_dict: Dict, check_format: bool = True):
        super().__init__()
        self.data = copy.deepcopy(input_dict)
        if check_format:
            self._check_format()

    @property
    def identifier(self) -> str:
        self._check_format()
        for ident, body in self.data.items():
            return ident
        raise Exception(f"{self} is a malformed")

    @property
    def body(self) -> Dict:
        self._check_format()
        for ident, body in self.data.items():
            return body

    @property
    def type(self) -> str:
        from pcs.component import Component  # Avoid circular import.

        return self.body[Component.TYPE_KEY]

    @property
    def as_kwargs(self) -> Dict:
        return {k: v for k, v in self.body.items() if k != "type"}

    def to_dict(self, flatten=False) -> Dict:
        from pcs.component import Component  # Avoid circular import.

        if flatten:
            result = {}
            result.update(self.body.copy())
            result[Component.IDENTIFIER_KEY] = self.identifier[:]
            return result
        else:
            return {self.identifier[:]: self.body.copy()}

    def get_and_extract_ident(self, key: str) -> str:
        return extract_identifier(self.body.get(key))

    def _check_format(self) -> None:
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

    def _update_identifier(self) -> None:
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
    def from_body(cls, body: Dict) -> "Spec":
        from pcs.component import Component  # Avoid circular import.

        assert is_spec_body(body), (
            "The dict provided is not a valid spec body."
        )
        ident_computed = Component.spec_body_to_identifier(body)
        return cls({ident_computed: body})

    @classmethod
    def from_flat(cls, flat_spec: Dict) -> "Spec":
        from pcs.component import Component  # Avoid circular import.

        assert Component.IDENTIFIER_KEY in flat_spec, (
            f"Key '{Component.IDENTIFIER_KEY}' not found in flat spec, "
            "you probably want to use Spec.from_body() instead."
        )
        ident_in = flat_spec.pop(Component.IDENTIFIER_KEY)
        spec = cls.from_body(flat_spec)
        assert spec.identifier == ident_in, (
            "The identifier in the provided flat_spec does not match the "
            "hash of the body (i.e. the dict provided minus the identifier) "
            "of the flat_spec provided."
        )
        return spec

    def to_flat(self) -> Dict:
        return flatten_spec(self.data)


def flatten_spec(nested_spec: Mapping) -> Dict:
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


def unflatten_spec(flat_spec: Mapping) -> Dict:
    """
    Takes a flat spec, and returns a nested spec. A nested spec is a map
    from the spec's identifier to a map of the specs other key->value
    attributes. A flat spec moves the identifier into the inner map,
    essentially flattening the outer two dictionaries into a single dictionary.

    :param flat_spec: a flat spec to unflatten.
    :return: Nested version of ``flat_spec``.
    """
    from pcs.component import Component  # Avoid circular import.

    assert Component.IDENTIFIER_KEY in flat_spec
    identifier = flat_spec[Component.IDENTIFIER_KEY]
    dup_spec = dict(copy.deepcopy(flat_spec))
    dup_spec.pop(Component.IDENTIFIER_KEY)
    return {identifier: dup_spec}


def is_flat_spec(spec: Mapping) -> bool:
    assert len(spec) > 0  # specs must have at least one key-value pair.
    # Flat specs must have an identifier in their outermost dict.
    from pcs.component import Component  # Avoid circular import.

    return Component.IDENTIFIER_KEY in spec
