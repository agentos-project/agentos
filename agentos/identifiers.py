class ComponentIdentifier(str):
    """
    A Component Identifier is an immutable string-like construct that encodes a
    name and, optionally, a version as a string using the '==' separator. It
    allows referring to Components both as [name] and [name]==[version] (e.g.,
    in registries or the command line).
    """
    def __new__(
        cls,
        identifier_or_name: str,
        version: str = None,
    ):
        assert not version and "==" in identifier_or_name, (
            f"When a version arg is passed during the creation of a "
            f"ComponentIdentifier, the first argument ({identifier_or_name}) "
            f"is interpreted as a name and so is not allowed to contain '=='."
            f"You probably don't need to pass in the version explicitly."
        )
        if version:
            obj = str.__new__(cls, f"{identifier_or_name}=={version}")
            obj.version = version
        else:
            obj = str.__new__(cls, identifier_or_name)
        obj._name = identifier_or_name
        return obj


# Like MLflow, we use strings as RunIdentifiers, per
# https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/entities/run_info.py#L99
RunIdentifier = str

RunCommandIdentifier = str

RepoIdentifier = str
