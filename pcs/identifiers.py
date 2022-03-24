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
        if version:
            assert "==" not in identifier_or_name, (
                f"When a version arg is passed during the creation of a "
                "ComponentIdentifier, the first argument "
                f"({identifier_or_name}) is interpreted as a name and so is "
                "not allowed to contain '=='. Since your first argument "
                "contains an '==', you probably don't need to pass in the "
                "version explicitly."
            )
            obj = str.__new__(cls, f"{identifier_or_name}=={version}")
            obj.name = identifier_or_name
            obj.version = version
        else:
            obj = str.__new__(cls, identifier_or_name)
            parts = identifier_or_name.split("==")
            assert 0 < len(parts) <= 2, (
                f"identifier_or_name '{identifier_or_name}' cannot be blank "
                "and cannot have more than one '==' in it."
            )
            if len(parts) == 2:
                obj.name = parts[0]
                obj.version = parts[1]
            else:
                obj.name = identifier_or_name
                obj.version = None
        return obj


# Like MLflow, we use strings as RunIdentifiers, per
# https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/entities/run_info.py#L99
RunIdentifier = str

RunCommandIdentifier = str

RepoIdentifier = str
