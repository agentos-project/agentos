import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

from mlflow.utils.mlflow_tags import MLFLOW_RUN_NAME

from pcs.exceptions import PythonComponentSystemException
from pcs.identifiers import RunIdentifier
from pcs.registry import InMemoryRegistry, Registry
from pcs.run import Run
from pcs.run_command import RunCommand
from pcs.specs import RunSpec, flatten_spec, unflatten_spec


def active_component_run(
    caller: Any, fail_if_none: bool = False
) -> Optional[Run]:
    """
    A helper function, returns the currently active ComponentRun, if it exists,
    else None. More specifically, if the caller is an object that is managed by
    a Component (i.e. if it has a __component__ attribute) that itself has an
    active_run, return that Run.

    :param caller: the managed object to fetch the active component run for.
    :param fail_if_none: if no active component run found, throw an exception
        instead of returning None.
    :return: the active component run if it exists, else None.
    """
    from pcs.component import Component

    if isinstance(caller, Component):
        component = caller
    else:
        try:
            component = caller.__component__
        except AttributeError:
            raise PythonComponentSystemException(
                "active_run() was called on an object that is not "
                "managed by a Component. Specifically, the object passed "
                "to active_run() must have a ``__component__`` attribute."
            )
    if not component.active_run:
        if fail_if_none:
            raise PythonComponentSystemException(
                "active_run() was passed an object managed by a Component "
                "with no active_run, and fail_if_no_active_run flag was "
                "True."
            )
        else:
            return None
    else:
        return component.active_run


class ComponentRun(Run):
    IS_FROZEN_KEY = "agentos.spec_is_frozen"
    IS_COMPONENT_RUN_TAG = "pcs.is_component_run"
    RUN_COMMAND_ID_KEY = "pcs.run_command_id"
    RUN_COMMAND_REGISTRY_FILENAME = "pcs.run_command_registry.yaml"
    """
    A ComponentRun represents the execution of a specific entry point of a
    specific Component with a specific ArgumentSet.
    """

    def __init__(
        self,
        run_command: RunCommand = None,
        experiment_id: str = None,
        existing_run_id: str = None,
    ) -> None:
        assert (
            run_command or existing_run_id
        ), "One of 'run_command' or 'existing_run_id' must be provided."
        super().__init__(
            experiment_id=experiment_id, existing_run_id=existing_run_id
        )
        assert not (
            run_command and existing_run_id
        ), "`run_command` cannot be passed with `existing_run_id`."
        self._run_command = None
        if run_command:
            self.set_and_log_run_command(run_command)
        else:
            self._run_command = self._fetch_run_command()
        self.set_tag(self.IS_COMPONENT_RUN_TAG, "True")
        self.set_tag(
            MLFLOW_RUN_NAME,
            f"PCS Component '{self.run_command.component.identifier}' "
            f"at Entry Point '{self.run_command.entry_point}'",
        )
        self._return_value = None

    @property
    def run_command(self) -> "RunCommand":
        return self._run_command

    @property
    def return_value(self) -> str:
        return self._return_value

    @property
    def is_reproducible(self) -> bool:
        return bool(self.run_command)

    @classmethod
    def from_run_command(
        cls, run_command: RunCommand, experiment_id: str = None
    ) -> "ComponentRun":
        return cls(run_command=run_command, experiment_id=experiment_id)

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        force: bool = False,
        include_artifacts: bool = False,
    ) -> Registry:
        if not registry:
            registry = InMemoryRegistry()
        spec = registry.get_run_spec(self.identifier, error_if_not_found=False)
        if spec and not force:
            assert spec == self.to_spec(), (
                f"A component run spec with identifier '{self.identifier}' "
                f"already exists in registry '{registry}' and differs from "
                "the one being added. Use force=True to overwrite the "
                "existing one.:\n\n"
                f"{spec}\n\n"
                f"{self.to_spec()}"
            )
        if recurse:
            self.run_command.to_registry(
                registry, recurse=recurse, force=force
            )
        return super().to_registry(
            registry, include_artifacts=include_artifacts, force=force
        )

    @classmethod
    def from_registry(
        cls, registry: Registry, identifier: RunIdentifier
    ) -> "ComponentRun":
        spec = registry.get_run_spec(identifier)
        return cls.from_spec(spec, registry)

    @classmethod
    def from_spec(cls, spec: Mapping, registry: Registry) -> "ComponentRun":
        flat_spec = flatten_spec(spec)
        run_command = RunCommand.from_registry(
            registry, flat_spec["run_command"]
        )
        w_run_cmd_from_mlflow = cls(existing_run_id=flat_spec["identifier"])
        assert w_run_cmd_from_mlflow.run_command == run_command, (
            "The RunCommand object created from the MLflow Run "
            f"'{flat_spec['identifier']}' is different from the one fetched"
            f"from the registry provided '{registry}'."
        )
        return w_run_cmd_from_mlflow

    def _fetch_run_command(self) -> RunCommand:
        try:
            path = self.download_artifacts(self.RUN_COMMAND_REGISTRY_FILENAME)
        except IOError as e:
            raise IOError(
                f"RunCommand registry artifact not found in Run with id "
                f"{self._mlflow_run_id}. {repr(e)}"
            )
        assert self.RUN_COMMAND_ID_KEY in self._mlflow_run.data.tags, (
            f"{self.RUN_COMMAND_ID_KEY} not found in the tags of MLflow "
            f"run with id {self._mlflow_run_id}."
        )
        run_command_id = self._mlflow_run.data.tags[self.RUN_COMMAND_ID_KEY]
        registry = Registry.from_yaml(path)
        return RunCommand.from_registry(registry, run_command_id)

    def set_and_log_run_command(self, run_command: RunCommand) -> None:
        """
        Log a Registry YAML file for the RunCommand of this run, including
        the ArgumentSet, entry_point (i.e., function name), component ID,
        as well as the root component being run and its full
        transitive dependency graph of other components as part of this Run.
        This registry file will contain the component spec and repo spec for
        each component in the root component's dependency graph. Note that a
        Run object contains a component object and thus the root component's
        full dependency graph of other components, and as such does not depend
        on a Registry to provide reproducibility. Like a Component, a Run
        (including its entry point, argument_set, root component, and the root
        component's full dependency graph) can be dumped into a Registry for
        sharing purposes, which essentially normalizes the Run's root
        component's dependency graph into flat component specs.
        """
        assert not self._run_command
        self._run_command = run_command
        self._validate_no_run_command_logged()
        self.set_tag(self.RUN_COMMAND_ID_KEY, run_command.identifier)
        run_command_dict = run_command.to_registry().to_dict()
        self.log_dict(run_command_dict, self.RUN_COMMAND_REGISTRY_FILENAME)

    def _validate_no_run_command_logged(self):
        assert self.RUN_COMMAND_ID_KEY not in self._mlflow_run.data.tags, (
            f"{self.RUN_COMMAND_ID_KEY} already found tags of MLflow run "
            f"with id {self._mlflow_run_id}. A run_command can only be logged "
            "once per a Run."
        )
        artifact_paths = [a.path for a in self.list_artifacts()]
        assert self.RUN_COMMAND_REGISTRY_FILENAME not in artifact_paths, (
            f"An artifact with name {self.RUN_COMMAND_REGISTRY_FILENAME} "
            "has already been logged to the MLflow run with id "
            f"{self._mlflow_run_id}. A run_command can only be logged "
            "once per a Run."
        )

    def log_return_value(
        self,
        ret_val: Any,
        format: str = "pickle",
    ):
        """
        Logs the return value of an entry_point run using the specified
        serialization format.

        :param ret_val: The Python object returned by this Run to be logged.
        :param format: Valid values are 'pickle, 'json', or 'yaml'.
        """
        assert (
            not self._return_value
        ), "return_value has already been logged and can only be logged once."
        self._return_value = ret_val
        tmp_dir_path = Path(tempfile.mkdtemp())
        filename_base = tmp_dir_path / (self.identifier + "-return_value")
        if format == "pickle":
            import pickle

            filename = filename_base.parent / (filename_base.name + ".pickle")
            with open(filename, "wb") as f:
                pickle.dump(ret_val, f)
        elif format == "json":
            import json

            filename = filename_base.parent / (filename_base.name + ".json")
            with open(filename, "w") as f:
                json.dump(ret_val, f)
        elif format == "yaml":
            import yaml

            filename = filename_base.parent / (filename_base.name + ".yaml")
            with open(filename, "w") as f:
                yaml.dump(ret_val, f)
        else:
            raise PythonComponentSystemException(
                f"Invalid format provided: {format}"
            )
        self.log_artifact(str(filename))
        filename.unlink()

    @property
    def is_publishable(self) -> bool:
        # use like: filtered_tags["is_publishable"] = self.is_publishable
        try:
            return self._mlflow_run.data.tags[self.IS_FROZEN_KEY] == "True"
        except KeyError:
            return False

    def to_spec(self, flatten: bool = False) -> RunSpec:
        flat_spec = super().to_spec(flatten=True)
        assert (
            self.run_command
        ), "Every ComponentRun instance must have a run_command."
        flat_spec["run_command"] = self.run_command.identifier
        return flat_spec if flatten else unflatten_spec(flat_spec)
