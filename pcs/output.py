import copy
import json
import pickle
import tempfile
from pathlib import Path
from typing import Any, Optional

import yaml
from mlflow.utils.mlflow_tags import MLFLOW_RUN_NAME

from pcs.command import Command
from pcs.exceptions import PythonComponentSystemException
from pcs.mlflow_run import MLflowRun
from pcs.registry import Registry


class Output(MLflowRun):
    IS_FROZEN_KEY = "agentos.spec_is_frozen"
    IS_COMPONENT_RUN_TAG = "pcs.is_component_run"
    COMMAND_ID_KEY = "pcs.command_id"
    COMMAND_REGISTRY_FILENAME = "pcs.command_registry.yaml"
    """
    Output from running a Command.

    As its name implies, an Output documents an instance of code execution
    and records output associated with it (similar to a logger). This is also
    called "tracking" by the MLflow project (and this class's parent is
    MLflowRun, which is a wrapper around the the MLflowRun abstraction).

    In addition to tracking the output of a code that was run, an Output
    can also be used for reproducibility: an Output has a member called a
    `command` that can be used to perform a "re-run" of the the same function
    with the same inputs (function/code, arguments, versioned dependency graph,
    etc.).
    """

    def __init__(
        self,
        command: Command,
        experiment_id: str = None,
    ) -> None:
        super().__init__(experiment_id=experiment_id)
        self._return_value = None
        self._command = command
        self._register_output_attributes()
        self._log_command()
        self.set_tag(self.IS_COMPONENT_RUN_TAG, "True")
        self.set_tag(
            MLFLOW_RUN_NAME,
            f"Running function '{self.command.function_name}' on Component "
            f"'{self.command.component.identifier[0:7]}'.",
        )

    @classmethod
    def from_existing_mlflow_run(cls, run_id: str) -> "Output":
        output = super().from_existing_mlflow_run(run_id)
        output._command = output._fetch_command()
        output._register_output_attributes()
        return output

    def _register_output_attributes(self):
        self.register_attribute("command")

    @property
    def command(self) -> "Command":
        return self._command

    @property
    def return_value(self) -> str:
        return self._return_value

    @property
    def is_reproducible(self) -> bool:
        return bool(self.command)

    @classmethod
    def from_command(
        cls, command: Command, experiment_id: str = None
    ) -> "Output":
        return cls(command=command, experiment_id=experiment_id)

    def _fetch_command(self) -> Command:
        try:
            path = self.download_artifacts(self.COMMAND_REGISTRY_FILENAME)
        except OSError as e:
            raise OSError(
                f"Command registry artifact not found in Run with id "
                f"{self._mlflow_run_id}. {repr(e)}"
            )
        assert self.COMMAND_ID_KEY in self.data["tags"], (
            f"{self.COMMAND_ID_KEY} not found in the tags of MLflow "
            f"run with id {self._mlflow_run_id}."
        )
        command_id = self._mlflow_run.data.tags[self.COMMAND_ID_KEY]
        registry = Registry.from_yaml(path)
        return Command.from_registry(registry, command_id)

    def _log_command(self) -> None:
        """
        Log a Registry YAML file for the Command of this run, including
        the ArgumentSet, function_name (i.e., function name), component ID,
        as well as the root component being run and its full
        transitive dependency graph of other components as part of this Run.
        This registry file will contain the component spec and repo spec for
        each component in the root component's dependency graph. Note that a
        Run object contains a component object and thus the root component's
        full dependency graph of other components, and as such does not depend
        on a Registry to provide reproducibility. Like a Module, a Run
        (including its entry point, argument_set, root component, and the root
        component's full dependency graph) can be dumped into a Registry for
        sharing purposes, which essentially normalizes the Run's root
        component's dependency graph into flat component specs.
        """
        self._validate_no_command_logged()
        self.set_tag(self.COMMAND_ID_KEY, self._command.identifier)
        command_dict = self._command.to_registry().to_dict()
        self.log_dict(command_dict, self.COMMAND_REGISTRY_FILENAME)

    def _validate_no_command_logged(self):
        assert self.COMMAND_ID_KEY not in self._mlflow_run.data.tags, (
            f"{self.COMMAND_ID_KEY} already found tags of MLflow run "
            f"with id {self._mlflow_run_id}. A command can only be logged "
            "once per a Run."
        )
        artifact_paths = [a.path for a in self.list_artifacts()]
        assert self.COMMAND_REGISTRY_FILENAME not in artifact_paths, (
            f"An artifact with name {self.COMMAND_REGISTRY_FILENAME} "
            "has already been logged to the MLflow run with id "
            f"{self._mlflow_run_id}. A command can only be logged "
            "once per a Run."
        )

    def log_return_value(
        self,
        ret_val: Any,
        format: str = "pickle",
    ):
        """
        Logs the return value of an function_name run using the specified
        serialization format.

        :param ret_val: The Python object returned by this Run to be logged.
        :param format: Valid values are 'pickle, 'json', or 'yaml'.
        """
        assert (
            not self._return_value
        ), "return_value has already been logged and can only be logged once."
        try:
            copy.deepcopy(ret_val)
            deep_copy_ok = True
        except RuntimeError:  # Make sure output type supports deepcopy.
            deep_copy_ok = False
        if deep_copy_ok:
            self._return_value = ret_val
        else:
            self._return_value = str(ret_val)
        tmp_dir_path = Path(tempfile.mkdtemp())
        filename_base = tmp_dir_path / (self.identifier + "-return_value")
        if format == "pickle":
            filename = filename_base.parent / (filename_base.name + ".pickle")
            with open(filename, "wb") as f:
                pickle.dump(ret_val, f)
        elif format == "json":
            filename = filename_base.parent / (filename_base.name + ".json")
            with open(filename, "w") as f:
                json.dump(ret_val, f)
        elif format == "yaml":
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


def active_output(caller: Any, fail_if_none: bool = False) -> Optional[Output]:
    """
    A helper function, returns the currently active Output, if it exists,
    else None. More specifically, if the caller is an object that is managed by
    a Module (i.e. if it has a __component__ attribute) that itself has an
    active_output, return that Run.

    :param caller: the managed object to fetch the active component run for.
    :param fail_if_none: if no active component run found, throw an exception
        instead of returning None.
    :return: the active component run if it exists, else None.
    """
    from pcs import Module

    if isinstance(caller, Module):
        component = caller
    else:
        try:
            component = caller.__component__
        except AttributeError:
            raise PythonComponentSystemException(
                "active_output() was called on an object that is not "
                "managed by a Module. Specifically, the object passed "
                "to active_output() must have a ``__component__`` attribute."
            )
    if not component.active_output:
        if fail_if_none:
            raise PythonComponentSystemException(
                "active_output() was passed an object managed by a Component "
                "with no active_output, and fail_if_no_active_output flag was "
                "True."
            )
        else:
            return None
    else:
        return component.active_output
