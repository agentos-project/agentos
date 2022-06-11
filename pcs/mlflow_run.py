import pprint
from functools import partial
from pathlib import Path
from typing import Sequence

from mlflow.entities import RunStatus
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from mlflow.tracking.context import registry as context_registry
from mlflow.utils.mlflow_tags import MLFLOW_PARENT_RUN_ID

from pcs.component import Component

SPEC_ATTRS = ["experiment_id", "info", "data"]


class MLflowRun(Component):
    """
    A wrapper around MLflow Run.

    An MLflowRun is similar to a logger but provides a bit more structure than
    loggers traditionally do. For example, instead of just a log-level and some
    free text, which is the typical interface for a logger, a Run allows
    recording of tags, parameters, and metrics. These each have their own
    semantics and each is represented as a key-value pair.

    An MLflowRun is a thin container that holds an RunData and RunInfo object.
    RunInfo contains the run metadata (id, user, timestamp, etc.)
    RunData contains metrics, params, and tags; each of which is a dict.

    PCS related abstractions are encoded into an MLflowRun as follows:
    - Registry -> MLflow artifact file
    - Function Name (string) -> MLflow run tag (MlflowRun.data.tags entry)
    - ArgumentSet -> MLflow artifact file

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
    # Run's mlflow_client. All of these take mlflow_run_id as
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
        super().__init__()
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
        self._register_attributes(SPEC_ATTRS)

    @classmethod
    def from_existing_mlflow_run(cls, run_id: str) -> "MLflowRun":
        try:
            cls.MLFLOW_CLIENT.get_run(run_id)
        except MlflowException as mlflow_exception:
            print(
                "Error: When creating an AgentOS Run using an "
                "existing MLflow Run ID, an MLflow run with that ID must "
                "be available at the current tracking URI, and "
                f"mlflow_run_id {run_id} is not."
            )
            raise mlflow_exception

        orig_init = cls.__init__
        cls.__init__ = Component.__init__
        try:
            run = cls()
            run._mlflow_run_id = run_id
        finally:
            cls.__init__ = orig_init

        run._mlflow_run_id = run_id
        run._register_attributes(SPEC_ATTRS)
        return run

    @classmethod
    def run_exists(cls, mlflow_run_id) -> bool:
        try:
            cls.MLFLOW_CLIENT.get_run(mlflow_run_id)
            return True
        except MlflowException:
            return False

    @classmethod
    def get_all_runs(cls):
        mlflow_runs = cls._get_all_mlflow_runs()
        res = []
        for mlflow_run in mlflow_runs:
            r = cls.from_existing_mlflow_run(mlflow_run.info.run_id)
            res.append(r)
        return res

    @classmethod
    def _get_all_mlflow_runs(cls):
        return cls.MLFLOW_CLIENT.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.PCS_RUN_TAG} ILIKE "%"',
        )

    @property
    def _mlflow_run(self):
        return self.MLFLOW_CLIENT.get_run(self._mlflow_run_id)

    @property
    def mlflow_run_id(self) -> str:
        return self._mlflow_run_id

    @property
    def data(self) -> dict:
        return self._mlflow_run.data.to_dictionary()

    @property
    def info(self) -> dict:
        return dict(self._mlflow_run.info)

    @property
    def experiment_id(self):
        return self._mlflow_run.info.experiment_id

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

    def _register_attributes(self, attributes: Sequence[str]):
        for attribute in attributes:
            self.register_attribute(attribute)

    def _check_initialization(self):
        assert self._mlflow_run_id
        assert self.data["tags"].get(self.PCS_RUN_TAG) == "True"
        self._check_attributes_registered(SPEC_ATTRS)

    def _check_attributes_registered(self, attributes):
        for attribute in attributes:
            error_msg = f"Attribute {attribute} is not registered"
            assert self.attribute_is_registered(attribute), error_msg

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
                for k, v in self.data["tags"].items()
                if not k.startswith("mlflow.")
            }
            print(f"    Run {self.mlflow_run_id}: {filtered_tags}")
        else:
            pprint.pprint(self.to_spec())

    @classmethod
    def print_all_status(cls) -> None:
        runs = cls.get_all_runs()
        print("\nRuns:")
        for run in runs:
            run.print_status()
        print()

    def get_child_mlflow_runs(self):
        mlflow_runs = self._get_all_mlflow_runs()
        children_runs = []
        for run in mlflow_runs:
            parent_mlflow_id = run.data.tags.get(MLFLOW_PARENT_RUN_ID)
            if self._mlflow_run_id == parent_mlflow_id:
                children_runs.append(run)
        return children_runs

    def __enter__(self) -> "MLflowRun":
        return self

    def __exit__(self, type, value, traceback) -> None:
        if type:
            self.set_terminated(RunStatus.to_string(RunStatus.FAILED))
            return
        else:
            self.end()
