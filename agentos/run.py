import os
import sys
import yaml
import mlflow
import pprint
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, TYPE_CHECKING
from contextlib import contextmanager
from mlflow.entities import Run as MLflowRun
from agentos.registry import Registry, web_registry
from agentos.parameter_set import ParameterSet
from agentos.repo import BadGitStateException, NoLocalPathException

# Avoids cicular imports
if TYPE_CHECKING:
    from agentos import Component


class Run:
    MLFLOW_EXPERIMENT_ID = "0"
    PARAM_KEY = "parameter_set.yaml"
    SPEC_KEY = "components.yaml"
    FROZEN_KEY = "spec_is_frozen"
    ROOT_NAME_KEY = "root_name"
    ENTRY_POINT_KEY = "entry_point"

    def __init__(self, mlflow_run: MLflowRun):
        self._mlflow_run = mlflow_run

    @staticmethod
    def get_all_runs() -> List["Run"]:
        run_infos = mlflow.list_run_infos(
            experiment_id=Run.MLFLOW_EXPERIMENT_ID,
            order_by=["attribute.end_time DESC"],
        )
        runs = [
            mlflow.get_run(run_id=run_info.run_id) for run_info in run_infos
        ]
        runs = [mlflow.active_run()] + runs
        runs = [run for run in runs if run is not None]
        return [Run(mlflow_run=run) for run in runs]

    @staticmethod
    def get_latest_publishable_run() -> Optional["Run"]:
        all_runs = Run.get_all_runs()
        publishable = [run for run in all_runs if run.is_publishable]
        if len(publishable) == 0:
            return None
        else:
            return publishable[0]

    @staticmethod
    def run_exists(run_id: Optional[str]) -> bool:
        return Run.get_by_id(run_id) is not None

    @staticmethod
    def get_by_id(run_id: Optional[str]) -> Optional["Run"]:
        run_map = {run.id: run for run in Run.get_all_runs()}
        return run_map.get(run_id)

    @staticmethod
    def print_all_status() -> None:
        runs = Run.get_all_runs()
        print("\nRuns:")
        for run in runs:
            run.print_status()
        print()

    @classmethod
    def active_run(cls):
        return cls(mlflow.active_run())

    @classmethod
    def log_param(self, name, value):
        mlflow.log_param(name, value)

    @classmethod
    def log_metric(self, name, value):
        mlflow.log_metric(name, value)

    @classmethod
    def set_tag(self, name, value):
        mlflow.set_tag(name, value)

    @classmethod
    def track(
        cls,
        root_component: "Component",
        fn_name: str,
        params: ParameterSet,
        tracked: bool,
    ):
        if not tracked:
            return cls._untracked_run()
        else:
            return cls._tracked_run(root_component, fn_name, params)

    @classmethod
    @contextmanager
    def _tracked_run(
        cls, root_component: "Component", fn_name: str, params: ParameterSet
    ):
        run = cls(mlflow.start_run(experiment_id=cls.MLFLOW_EXPERIMENT_ID))
        run.log_parameter_set(params)
        run.log_component_spec(root_component)
        run.log_call(root_component.identifier.full, fn_name)
        try:
            yield run
        finally:
            mlflow.end_run()

    @classmethod
    @contextmanager
    def _untracked_run(cls):
        try:
            yield None
        finally:
            pass

    @property
    def id(self) -> str:
        return self._mlflow_run.info.run_id

    @property
    def entry_point(self) -> str:
        return self._mlflow_run.data.params[self.ENTRY_POINT_KEY]

    @property
    def is_publishable(self) -> bool:
        return self._mlflow_run.data.params[self.FROZEN_KEY] == "True"

    @property
    def root_component(self) -> str:
        return self._mlflow_run.data.params[self.ROOT_NAME_KEY]

    @property
    def parameter_set(self) -> Dict:
        return self._get_yaml_artifact(self.PARAM_KEY)

    @property
    def component_spec(self) -> Dict:
        return self._get_yaml_artifact(self.SPEC_KEY)

    @property
    def tags(self) -> Dict:
        return self.mlflow_data.tags

    @property
    def metrics(self) -> Dict:
        return self.mlflow_data.metrics

    @property
    def params(self) -> Dict:
        return self.mlflow_data.params

    @property
    def mlflow_data(self):
        return self._mlflow_run.data

    @property
    def mlflow_info(self):
        return self._mlflow_run.info

    def _get_yaml_artifact(self, name: str) -> Dict:
        artifacts_dir_path = self.get_artifacts_dir_path()
        artifact_path = artifacts_dir_path / name
        if not artifact_path.is_file():
            return {}
        with artifact_path.open() as file_in:
            return yaml.safe_load(file_in)

    def get_artifacts_dir_path(self) -> Path:
        artifacts_uri = self.mlflow_info.artifact_uri
        if "file://" != artifacts_uri[:7]:
            raise Exception(f"Non-local artifacts path: {artifacts_uri}")
        slice_count = 7
        if sys.platform in ["win32", "cygwin"]:
            slice_count = 8
        return Path(artifacts_uri[slice_count:]).absolute()

    def print_status(self, detailed: bool = False) -> None:
        if not detailed:
            filtered_tags = {
                k: v
                for k, v in self.tags.items()
                if not k.startswith("mlflow.")
            }
            filtered_tags["is_publishable"] = self.is_publishable
            print(f"\tRun {self.id}: {filtered_tags}")
        else:
            pprint.pprint(self.to_dict())

    def to_dict(self) -> Dict:
        artifact_paths = [str(p) for p in self._get_artifact_paths()]
        mlflow_info_dict = {
            "artifact_uri": self.mlflow_info.artifact_uri,
            "end_time": self.mlflow_info.end_time,
            "experiment_id": self.mlflow_info.experiment_id,
            "lifecycle_stage": self.mlflow_info.lifecycle_stage,
            "run_id": self.mlflow_info.run_id,
            "run_uuid": self.mlflow_info.run_uuid,
            "start_time": self.mlflow_info.start_time,
            "status": self.mlflow_info.status,
            "user_id": self.mlflow_info.user_id,
        }
        return {
            "id": self.id,
            "is_publishable": self.is_publishable,
            "root_component": self.root_component,
            "entry_point": self.entry_point,
            "parameter_set": self.parameter_set,
            "component_spec": self.component_spec,
            "artifacts": artifact_paths,
            "mlflow_info": mlflow_info_dict,
            "mlflow_data": self.mlflow_data.to_dictionary(),
        }

    def _get_artifact_paths(self) -> List[Path]:
        artifacts_dir = self.get_artifacts_dir_path()
        artifact_paths = []
        skipped_artifacts = [
            self.PARAM_KEY,
            self.SPEC_KEY,
        ]
        for name in os.listdir(self.get_artifacts_dir_path()):
            if name in skipped_artifacts:
                continue
            artifact_paths.append(artifacts_dir / name)

        exist = [p.exists() for p in artifact_paths]
        assert all(exist), f"Missing artifact paths: {artifact_paths}, {exist}"
        return artifact_paths

    def publish(self) -> None:
        run_id = self.to_registry(web_registry)
        print(f"Published Run {run_id} to {web_registry.root_url}.")

    def to_registry(self, registry: Registry) -> str:
        if not self.is_publishable:
            raise Exception("Run not publishable; Spec is not frozen!")
        result = registry.push_run_data(self.to_dict())
        run_id = result["id"]
        registry.push_run_artifacts(run_id, self._get_artifact_paths())
        return run_id

    def log_parameter_set(self, params: ParameterSet) -> None:
        self.log_data_as_yaml_artifact(self.PARAM_KEY, params.to_spec())

    def log_component_spec(self, root_component: "Component") -> None:
        frozen = None
        try:
            root_id = root_component.identifier
            frozen_reg = root_component.to_frozen_registry()
            frozen = frozen_reg.get_component_spec_by_id(root_id)
            self.log_data_as_yaml_artifact(self.SPEC_KEY, frozen)
        except (BadGitStateException, NoLocalPathException) as exc:
            print(f"Warning: component is not publishable: {str(exc)}")
            spec = root_component.to_spec()
            self.log_data_as_yaml_artifact(self.SPEC_KEY, spec)
        mlflow.log_param(self.FROZEN_KEY, frozen is not None)

    def log_call(self, root_name: str, fn_name: str) -> None:
        mlflow.log_param(self.ROOT_NAME_KEY, root_name)
        mlflow.log_param(self.ENTRY_POINT_KEY, fn_name)

    def log_data_as_yaml_artifact(self, name: str, data: dict):
        try:
            tmp_dir_path = Path(tempfile.mkdtemp())
            artifact_path = tmp_dir_path / name
            with open(artifact_path, "w") as file_out:
                file_out.write(yaml.safe_dump(data))
            mlflow.log_artifact(artifact_path)
        finally:
            shutil.rmtree(tmp_dir_path)
