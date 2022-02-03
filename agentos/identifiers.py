class ComponentIdentifier:
    """
    A Component Identifier is an immutable string-like construct that encodes a
    name and, optionally, a version as a string using the '==' separator. It
    allows referring to Components both as [name] and [name]==[version] (e.g.,
    in registries or the command line).
    """

    @staticmethod
    def from_str(identifier_string: str) -> "ComponentIdentifier":
        split_identifier = str(identifier_string).split("==")
        assert (
            len(split_identifier) <= 2
        ), f"Bad identifier: '{identifier_string}'"
        if len(split_identifier) == 1:
            return ComponentIdentifier(split_identifier[0])
        else:
            return ComponentIdentifier(
                split_identifier[0], split_identifier[1]
            )

    def __init__(
        self,
        name: str,
        version: str = None,
    ):
        assert "==" not in name, (
            f"Component.Identifier ({name} is not allowed to contain '=='."
            f"You should probably use Component.Identifier.from_str() instead."
        )
        self._name = name
        self._version = version

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def full(self) -> str:
        if self._name and self._version:
            return "==".join((self._name, self._version))
        return self._name

    def __repr__(self) -> str:
        return f"<agentos.component.Component.Identifer: {self.full}>"

    def __hash__(self) -> int:
        return hash(self.full)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.full == other.full
        elif isinstance(other, str):
            return self.full == other
        else:
            return self is other

    def __str__(self):
        return self.full


# Like MLflow, we use strings as RunIdentifiers, per
# https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/entities/run_info.py#L99
RunIdentifier = str

RunCommandIdentifier = str

RepoIdentifier = str
