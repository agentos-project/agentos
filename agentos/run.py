import pprint
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Sequence
from mlflow.exceptions import MlflowException
from mlflow.entities import RunStatus
from mlflow.tracking import MlflowClient
from agentos.registry import Registry
from agentos.exceptions import PythonComponentSystemException
from agentos.specs import RunSpec
from agentos.identifiers import RunIdentifier


class Run:
    """
    Conceptually, a Run represents code execution. More specifically, a Run has
    two distinct uses. First, a Run is used to document an instance of code
    execution and record output associated with it (similar to a logger).
    Second is reproducibility, and for this a Run can optionally hold a
    RunCommand, which, if it exists, can be used to recreate this run, i.e., to
    perform a re-run.

    Structurally, a Run is similar to a logger but provides a bit more
    structure than loggers traditionally do. For example, instead of just a log
    level free text, a Run allows recording of a tag, parameter, and a metric.
    These each have their own semantics and each is represented as a key-value
    pair. Currently, an AgentOS Run is a wrapper around an MLflow Run.

    An MLflow Run is a thin container that holds an RunData and RunInfo object.
    RunInfo contains the run metadata (id, user, timestamp, etc.)
    RunData contains metrics, params, and tags; each of which is a dict.

    AgentOS Run related abstractions are encoded into an MLflowRun as follows:
    - Component Registry incl. root, dependencies, repos -> artifact yaml file
    - Entry point string -> MLflow run tag (MlflowRun.data.tags entry)
    - ParameterSet -> artifact yaml file.
    """

    _mlflow_client = MlflowClient()

    DEFAULT_EXPERIMENT_ID = "0"
    PCS_RUN_TAG = "pcs.is_run"
    # Pass calls to the following functions through to this
    # Run's mlflow_client. All of these take run_id as
    # first arg, and so the pass-through logic also binds
    # self._mlflow_run_id as the first arg of the calls.
    PASS_THROUGH_FN_PREFIXES = [
        "log",
        "set_tag",
        "list_artifacts",
        "search_runs",
        "set_terminated",
        "download_artifacts",
    ]

    def __init__(
        self,
        experiment_id: str = None,
        existing_run_id: str = None,
    ) -> None:
        """
        Consider using class factory methods instead of directly using
        __init__. For example: Run.from_run_command(),
        Run.from_existing_run_id().

        :param experiment_id: Optional Experiment ID.
        :param existing_run_id: Optional Run ID.
        """
        self._return_value = None
        if existing_run_id:
            assert (
                not experiment_id
            ), "`existing_run_id` cannot be passed with `experiment_id`"
            try:
                self._mlflow_client.get_run(existing_run_id)
            except MlflowException as mlflow_exception:
                print(
                    "Error: When creating an AgentOS Run using an "
                    "existing MLflow Run ID, an MLflow run with that ID must "
                    "be available at the current tracking URI, and "
                    f"run_id {existing_run_id} is not."
                )
                raise mlflow_exception
            self._mlflow_run_id = existing_run_id
        else:  # new run
            if experiment_id:
                exp_id = experiment_id
            else:
                exp_id = self.DEFAULT_EXPERIMENT_ID
            new_run = self._mlflow_client.create_run(exp_id)
            self._mlflow_run_id = new_run.info.run_id
            self.set_tag(self.PCS_RUN_TAG, "True")

    def __del__(self):
        self._mlflow_client.set_terminated(self._mlflow_run_id)

    @classmethod
    def run_exists(cls, run_id) -> bool:
        try:
            cls._mlflow_client.get_run(run_id)
            return True
        except MlflowException:
            return False

    @classmethod
    def get_all_runs(cls):
        mlflow_runs = cls._mlflow_client.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.PCS_RUN_TAG} ILIKE "%"',
        )
        print(f"{len(mlflow_runs)} mlflow_runs")
        print(mlflow_runs)
        res = []
        for mlflow_run in mlflow_runs:
            r = Run.from_existing_run_id(mlflow_run.info.run_id)
            print(r)
            res.append(r)
        return res

    @classmethod
    def from_existing_run_id(cls, run_id: RunIdentifier) -> "Run":
        return cls(existing_run_id=run_id)

    @classmethod
    def from_tracking_store(cls, run_id: RunIdentifier):
        return cls.from_existing_run_id(run_id)

    @staticmethod
    def active_run(caller: Any, fail_if_no_active_run: bool = False) -> "Run":
        """
        A helper function.
        """
        from agentos.component import Component

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
            if fail_if_no_active_run:
                raise PythonComponentSystemException(
                    "active_run() was passed an object managed by a Component "
                    "with no active_run, and fail_if_no_active_run flag was "
                    "True."
                )
            else:
                run = Run()
                if isinstance(caller, Component):
                    print(
                        "Warning: the object passed to active_run() is "
                        "managed by a Component that has no active_run. "
                        f"Returning a new run (id: {run.identifier} that is "
                        "not associated with any Run object."
                    )
            return run
        else:
            return component.active_run

    @property
    def _mlflow_run(self):
        return self._mlflow_client.get_run(self._mlflow_run_id)

    @property
    def identifier(self) -> str:
        return self._mlflow_run.info.run_id

    @property
    def data(self) -> dict:
        return self._mlflow_run.data

    @property
    def info(self) -> dict:
        return self._mlflow_run.info

    def __getattr__(self, attr_name):
        prefix_matches = [
            attr_name.startswith(x) for x in self.PASS_THROUGH_FN_PREFIXES
        ]
        if any(prefix_matches):
            try:
                from functools import partial

                mlflow_client_fn = getattr(self._mlflow_client, attr_name)
                return partial(mlflow_client_fn, self._mlflow_run_id)
            except AttributeError as e:
                raise AttributeError(
                    f"No attribute '{attr_name}' could be found in either "
                    f"'{self.__class__} or the MlflowClient object it is "
                    f"wrapping. " + str(e)
                )
        else:
            raise AttributeError(
                f"type object '{self.__class__}' has no attribute "
                f"'{attr_name}'"
            )

    def _get_artifact_paths(self) -> Sequence[Path]:
        artifacts_dir = self.download_artifacts(".")
        artifact_paths = [
            Path(artifacts_dir) / a.path for a in self.list_artifacts()
        ]
        exist = [p.exists() for p in artifact_paths]
        assert all(exist), f"Missing artifact paths: {artifact_paths}, {exist}"
        return artifact_paths

    def end(
        self, status: str = RunStatus.to_string(RunStatus.FINISHED)
    ) -> None:
        """
        This is copied and adapted from MLflow's fluent api mlflow.end_run
        """
        self.set_terminated(status)

    def print_status(self, detailed: bool = False) -> None:
        if not detailed:
            filtered_tags = {
                k: v
                for k, v in self.data.tags.items()
                if not k.startswith("mlflow.")
            }
            print(f"\tRun {self.identifier}: {filtered_tags}")
        else:
            pprint.pprint(self.to_spec())

    @staticmethod
    def print_all_status() -> None:
        runs = Run.get_all_runs()
        print("\nRuns:")
        for run in runs:
            run.print_status()
        print()

    @classmethod
    def from_registry(
        cls,
        registry: Registry,
        run_id: RunIdentifier,
    ) -> "Run":
        # TODO figure out a way to deserialize an MLflowRun from the registry
        #     and reconcile that with what is in the tracking store.
        # run_spec = registry.get_run_spec(run_id)
        raise NotImplementedError

    def to_registry(
        self,
        registry: Registry = None,
        include_artifacts: bool = False,
    ) -> Registry:
        if not registry:
            from agentos.registry import InMemoryRegistry

            registry = InMemoryRegistry()
        registry.add_run_spec(self.to_spec())
        # If we are writing to a WebRegistry, have local artifacts, and
        # include_artifacts is True, try uploading the artifact files to the
        # registry.
        if (
            include_artifacts
            and hasattr(registry, "add_run_artifacts")
            and urlparse(self.info.artifact_uri).scheme == "file"
        ):
            local_artifact_path = self.get_artifacts_dir_path()
            registry.add_run_artifacts(self.identifier, local_artifact_path)
        return registry

    def to_spec(self, flatten: bool = False) -> RunSpec:
        return self._mlflow_run.to_dictionary()

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, type, value, traceback) -> None:
        if type:
            self.set_terminated(RunStatus.to_string(RunStatus.FAILED))
            return
        else:
            self.end()
