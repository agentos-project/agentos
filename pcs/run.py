import pprint
from functools import partial
from pathlib import Path
from typing import Sequence

from mlflow.entities import RunStatus
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from mlflow.tracking.context import registry as context_registry

from pcs.spec_object import Component


class MLflowRun(Component):
    """
    Conceptually, a Run represents code execution. More specifically, a Run has
    two distinct uses. First, a Run is used to document an instance of code
    execution and record output associated with it (similar to a logger).
    Second, a Run allows for reproducibility. For this a Run can optionally
    hold a Command that can be used to recreate this run, i.e., to
    perform a "re-run".

    We implement a Run that records its Command as a special type of Run
    called a :py.func.pcs.run_command.Output: which is a subclass
    of ``Run``.

    A Run is similar to a logger but provides a bit more structure than loggers
    traditionally do. For example, instead of just a log-level and some free
    text, which is the typical interface for a logger, a Run allows recording
    of tags, parameters, and metrics. These each have their own semantics and
    each is represented as a key-value pair. Currently, an AgentOS Run is a
    wrapper around an MLflow Run.

    An MLflow Run is a thin container that holds an RunData and RunInfo object.
    RunInfo contains the run metadata (id, user, timestamp, etc.)
    RunData contains metrics, params, and tags; each of which is a dict.

    AgentOS Run related abstractions are encoded into an MLflowRun as follows:
    - Module Registry -> MLflow artifact file
    - Entry point string -> MLflow run tag (MlflowRun.data.tags entry)
    - ArgumentSet -> MLflow artifact file

    A Run can also contain a [pointer to a] Command.

    A Run can also have pointers to other runs. These pointers can have
    different semantic meanings. They could have an "inner-outer" relationship,
    i.e., an outer run is already active when it's "inner" run starts and ends.
    Alternatively, two runs could have an "output-input dependency-depender"
    relationship, in which the depender uses the some part of dependency run's
    output as input. In this case, the relationship is causal.
    """

    # TODO: Decide if pointers to other runs should be special some how.

    MLFLOW_CLIENT = MlflowClient()

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

    def __init__(self, experiment_id: str = None) -> None:
        if experiment_id:
            exp_id = experiment_id
        else:
            exp_id = self.DEFAULT_EXPERIMENT_ID
        new_run = self.MLFLOW_CLIENT.create_run(exp_id)
        self._mlflow_run_id = new_run.info.run_id
        self.set_tag(self.PCS_RUN_TAG, "True")
        resolved_tags = context_registry.resolve_tags()
        for tag_k, tag_v in resolved_tags.items():
            self.set_tag(tag_k, tag_v)

    @classmethod
    def from_existing_run_id(cls, run_id: str) -> "Run":
        try:
            cls.MLFLOW_CLIENT.get_run(run_id)
        except MlflowException as mlflow_exception:
            print(
                "Error: When creating an AgentOS Run using an "
                "existing MLflow Run ID, an MLflow run with that ID must "
                "be available at the current tracking URI, and "
                f"run_id {run_id} is not."
            )
            raise mlflow_exception
        orig_init = cls.__init__
        cls.__init__ = lambda x: None
        try:
            run = cls()
            run._mlflow_run_id = run_id
        finally:
            cls.__init__ = orig_init
        return run

    @classmethod
    def run_exists(cls, run_id) -> bool:
        try:
            cls.MLFLOW_CLIENT.get_run(run_id)
            return True
        except MlflowException:
            return False

    @classmethod
    def get_all_runs(cls):
        mlflow_runs = cls.MLFLOW_CLIENT.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.PCS_RUN_TAG} ILIKE "%"',
        )
        res = []
        for mlflow_run in mlflow_runs:
            r = Run.from_existing_run_id(mlflow_run.info.run_id)
            res.append(r)
        return res

    @property
    def _mlflow_run(self):
        return self.MLFLOW_CLIENT.get_run(self._mlflow_run_id)

    @property
    def run_id(self) -> str:
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
                mlflow_client_fn = getattr(self.MLFLOW_CLIENT, attr_name)
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
            print(f"    Run {self.run_id}: {filtered_tags}")
        else:
            pprint.pprint(self.to_spec())

    @classmethod
    def print_all_status(cls) -> None:
        runs = cls.get_all_runs()
        print("\nRuns:")
        for run in runs:
            run.print_status()
        print()

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, type, value, traceback) -> None:
        if type:
            self.set_terminated(RunStatus.to_string(RunStatus.FAILED))
            return
        else:
            self.end()
