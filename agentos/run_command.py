from hashlib import sha1
from typing import TYPE_CHECKING
from agentos.registry import Registry
from agentos.specs import RunCommandSpec, RunCommandSpecKeys, unflatten_spec
from agentos.identifiers import RunIdentifier, RunCommandIdentifier
from agentos.run import Run

# Avoids circular imports
if TYPE_CHECKING:
    from agentos.component import Component
    from agentos.argument_set import ArgumentSet


class RunCommand:
    """
    A RunCommand contains everything required to reproducibly execute a
    Component Entry Point. Unlike a Run, a RunCommand is not concerned with the
    outputs of the execution (see :py:func:agentos.Run: for more on that.)

    You can think of a RunCommand as a glorified dictionary containing the
    pointers to arguments and versions of code necessary to reproduce the
    setting up of a component (including its dependency dag) and the execution
    of one of its entry points with a specific ArgumentSet. Whereas a Run
    itself (which may contain a RunCommand) is more like a client to a backing
    store used various types of outputs of the code being executed.

    Our concept of a RunCommand is inspired by the MLflow ``Project Run``
    abstraction. In MLflow runs of Projects (which are roughly analogous to our
    Components) are intertwined with MLflow's concept of Runs for tracking
    purposes. In MLflow, a Project Run is a wrapper around an MLflow tracking
    Run.

    In MLflow, an entry point exists in the context of a Project Run. A
    project Run uses Tags on the underlying tracking run to log all sorts of
    metadata, including the entry point, per
    https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/projects/utils.py#L225
    and
    https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/utils/mlflow_tags.py
    """

    def __init__(
        self,
        component: "Component",
        entry_point: str,
        argument_set: "ArgumentSet",
    ):
        self._component = component
        self._entry_point = entry_point
        self._argument_set = argument_set

    def __repr__(self) -> str:
        return f"<agentos.run_command.RunCommand: {self}>"

    def __hash__(self) -> int:
        return int(self._sha1(), 16)

    def _sha1(self) -> str:
        # Not positive if this is stable across architectures.
        # See https://stackoverflow.com/q/27522626
        hash_str = (
            self._component.identifier.full
            + self._entry_point
            + self._argument_set.identifier
        )
        return sha1(hash_str.encode("utf-8")).hexdigest()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return self is other

    def __str__(self):
        return str(hash(self))

    @property
    def identifier(self) -> str:
        return str(hash(self))

    @property
    def component(self):
        return self._component

    @property
    def entry_point(self):
        return self._entry_point

    @property
    def argument_set(self):
        return self._argument_set

    def new_run(self, experiment_id: str = None):
        return Run.from_run_command(self, experiment_id=experiment_id)

    @classmethod
    def from_default_registry(cls, run_id: RunIdentifier) -> "RunCommand":
        return cls.from_registry(Registry.from_default(), run_id)

    @classmethod
    def from_registry(
        cls,
        registry: Registry,
        run_command_id: RunCommandIdentifier,
    ) -> "RunCommand":
        run_cmd_spec = registry.get_run_command_spec(run_command_id)
        return cls.from_spec(run_cmd_spec, registry)

    @classmethod
    def from_spec(
        cls, run_cmd_spec: RunCommandSpec, registry: Registry
    ) -> "RunCommand":
        assert len(run_cmd_spec) == 1
        spec_identifier, inner_spec = None, None
        for key, value in run_cmd_spec.items():
            spec_identifier = key
            inner_spec = value
        component_id = inner_spec[RunCommandSpecKeys.COMPONENT_ID]
        from agentos.component import Component
        from agentos.argument_set import ArgumentSet

        component = Component.from_registry(registry, component_id)
        arg_set = ArgumentSet.from_spec(
            inner_spec[RunCommandSpecKeys.PARAMETER_SET]
        )
        new_run_cmd = cls(
            component=component,
            entry_point=inner_spec[RunCommandSpecKeys.ENTRY_POINT],
            argument_set=arg_set,
        )
        assert new_run_cmd.identifier == spec_identifier, (
            f"Identifier of new run_command {new_run_cmd.identifier} "
            "should match identifier of spec it was loaded from "
            f"{spec_identifier}, but they don't match."
        )
        return new_run_cmd

    def publish(self) -> None:
        """
        This function is like :py:func:to_registry: but it writes the
        RunCommand to the default registry, whereas :py:func:to_registry:
        writes the RunCommand either to an explicitly provided registry object,
        or to a new InMemoryRegistry.
        """
        if not self.is_publishable:
            raise Exception("RunCommand not publishable; Spec is not frozen!")
        default_registry = Registry.from_default()
        run_id = self.to_registry(default_registry)
        print(f"Published RunCommand {run_id} to {default_registry}.")

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        force: bool = False,
    ) -> Registry:
        """
        Returns a registry (which may optionally already exist) containing a
        run spec for this run. If recurse is True, also adds the component that
        was run to the registry by calling ``.to_registry()`` on it, and
        passing the given registry arg as well as the recurse and force args
        through to that call.

        For details on those flags, see :py:func:agentos.Component.to_registry:
        """
        if not registry:
            from agentos.registry import InMemoryRegistry

            registry = InMemoryRegistry()

        spec = registry.get_run_command_spec(
            self.identifier, error_if_not_found=False
        )
        if spec and not force:
            assert spec == self.to_spec(), (
                f"A run command spec with identifier '{self.identifier}' "
                f"already exists in registry '{registry}' and differs from "
                "the one being added. Use force=True to overwrite the "
                "existing one."
            )
        if recurse:
            self._component.to_registry(registry, recurse, force)
        registry.add_run_command_spec(self.to_spec())
        return registry

    def run(self) -> "Run":
        """
        Create a new run using the same root component, entry point, and
        params as this RunCommand.

        :return: a new RunCommand object representing the rerun.
        """
        return self.component.run_with_arg_set(
            self.entry_point, self.argument_set
        )

    def to_spec(self, flatten: bool = False) -> RunCommandSpec:
        flat_spec = {
            RunCommandSpecKeys.IDENTIFIER: self.identifier,
            RunCommandSpecKeys.COMPONENT_ID: self._component.identifier.full,
            RunCommandSpecKeys.ENTRY_POINT: self._entry_point,
            RunCommandSpecKeys.PARAMETER_SET: self._argument_set.to_spec(),
        }
        return flat_spec if flatten else unflatten_spec(flat_spec)
