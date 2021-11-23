import os
import sys
import yaml
import statistics
from pathlib import Path
from typing import List, Dict, Optional
from collections import namedtuple
import mlflow
from mlflow.entities import Run
from agentos import Component
from agentos.utils import MLFLOW_EXPERIMENT_ID


_EPISODE_KEY = "episode_count"
_STEP_KEY = "step_count"

_RUN_STATS_MEMBERS = [
    _EPISODE_KEY,
    _STEP_KEY,
    "max_reward",
    "median_reward",
    "mean_reward",
    "min_reward",
    "training_episode_count",
    "training_step_count",
]

RunStats = namedtuple("RunStats", _RUN_STATS_MEMBERS)


class AgentTracker:
    """
    A Component used to track Agent training and evaluation runs.
    """

    LEARN_KEY = "learn"
    RESET_KEY = "reset"
    EVALUATE_KEY = "evaluate"
    RUN_TYPE_TAG = "run_type"
    AGENT_NAME_KEY = "agent_name"
    ENV_NAME_KEY = "environment_name"

    def __init__(self, *args, **kwargs):
        self.episode_data = []

        def evaluate_run_manager(
            agent_name: str = None, environment_name: str = None
        ) -> RunContextManager:
            return RunContextManager(
                tracker=self,
                run_type=self.EVALUATE_KEY,
                agent_name=agent_name,
                environment_name=environment_name,
            )

        def learn_run_manager(
            agent_name: str = None, environment_name: str = None
        ) -> RunContextManager:
            return RunContextManager(
                tracker=self,
                run_type=self.LEARN_KEY,
                agent_name=agent_name,
                environment_name=environment_name,
            )

        self.evaluate_run = evaluate_run_manager
        self.learn_run = learn_run_manager
        self.run_type = None

    def start_run_type(self, run_type: str) -> None:
        self.run_type = run_type
        self._log_run_type()

    def log_agent_name(self, agent_name: str) -> None:
        mlflow.log_param(self.AGENT_NAME_KEY, agent_name)

    def log_environment_name(self, environment_name: str) -> None:
        mlflow.log_param(self.ENV_NAME_KEY, environment_name)

    def _log_run_type(self) -> None:
        mlflow.set_tag(self.RUN_TYPE_TAG, self.run_type)

    def publish(self) -> None:
        run = self._get_last_benchmark_run()
        if run is None:
            raise Exception("No evaluation run found!")
        data = {
            "metrics": run.data.metrics,
            "parameters": self._get_yaml_artifact(run, "parameter_set.yaml"),
            "component_spec": self._get_yaml_artifact(run, "agentos.yaml"),
            "agent_name": run.data.params.get(self.AGENT_NAME_KEY),
            "agent_exists": run.data.params.get("agent_exists"),
            "environment_name": run.data.params.get(self.ENV_NAME_KEY),
            "environment_exists": run.data.params.get("environment_exists"),
            "entry_point": run.data.params.get("entry_point"),
            "spec_is_frozen": run.data.params.get("spec_is_frozen"),
            "artifact_paths": self._get_artifact_paths(run),
        }
        import pprint

        pprint.pprint(data)
        # TODO - push run data to server
        # TODO - push artifacts to server

    def _get_artifact_paths(self, run):
        artifacts_dir = self._get_artifacts_dir(run)
        artifact_paths = []
        skipped_artifacts = [
            "parameter_set.yaml",
            "agentos.yaml",
            "frozen_agentos.yaml",
        ]
        for name in os.listdir(self._get_artifacts_dir(run)):
            if name in skipped_artifacts:
                continue
            artifact_paths.append(artifacts_dir / name)

        exist = [p.exists() for p in artifact_paths]
        assert all(exist), f"Missing artifact paths: {artifact_paths}, {exist}"
        return artifact_paths

    def _get_yaml_artifact(self, run: Run, name: str) -> Dict:
        artifacts_dir = self._get_artifacts_dir(run)
        artifact_path = artifacts_dir / name
        if not artifact_path.is_file():
            return {}
        with artifact_path.open() as file_in:
            return yaml.safe_load(file_in)

    def _get_artifacts_dir(self, run):
        artifacts_uri = run.info.artifact_uri
        if "file://" != artifacts_uri[:7]:
            raise Exception(f"Non-local artifacts path: {artifacts_uri}")
        slice_count = 7
        if sys.platform in ["win32", "cygwin"]:
            slice_count = 8
        return Path(artifacts_uri[slice_count:]).absolute()

    def _get_last_benchmark_run(self):
        runs = self._get_all_runs()
        for run in runs:
            if run.data.tags.get(self.RUN_TYPE_TAG) == self.EVALUATE_KEY:
                return run
        return None

    def log_run_metrics(self):
        assert self.episode_data, "No episode data!"
        assert mlflow.active_run() is not None
        run_stats = self._get_run_stats()
        for key in _RUN_STATS_MEMBERS:
            val = getattr(run_stats, key)
            mlflow.log_metric(key, val)

    def get_training_info(self) -> (int, int):
        runs = self._get_all_runs()
        total_episodes = 0
        total_steps = 0
        for run in runs:
            if run.data.tags.get(self.RUN_TYPE_TAG) == self.LEARN_KEY:
                total_episodes += int(run.data.metrics.get(_EPISODE_KEY, 0))
                total_steps += int(run.data.metrics.get(_STEP_KEY, 0))
        return total_episodes, total_steps

    def _get_all_runs(self, respect_reset: bool = True) -> List[Run]:
        assert mlflow.active_run() is not None
        run_infos = mlflow.list_run_infos(
            experiment_id=MLFLOW_EXPERIMENT_ID,
            order_by=["attribute.end_time DESC"],
        )
        runs = [
            mlflow.get_run(run_id=run_info.run_id) for run_info in run_infos
        ]
        runs = [mlflow.active_run()] + runs
        runs = [run for run in runs if run is not None]
        if respect_reset:
            latest_runs = []
            for run in runs:
                if run.data.tags.get(self.RUN_TYPE_TAG) == self.RESET_KEY:
                    break
                latest_runs.append(run)
            return latest_runs
        return runs

    def print_results(self):
        if not self.episode_data:
            return
        run_stats = self._get_run_stats()
        if self.run_type == self.LEARN_KEY:
            print(
                "\nTraining results over "
                f"{run_stats.episode_count} episodes:"
            )
            print(
                "\tOverall agent was trained on "
                f"{run_stats.training_step_count} transitions over "
                f"{run_stats.training_episode_count} episodes"
            )
        else:
            print(
                "\nBenchmark results over "
                f"{run_stats.episode_count} episodes:"
            )
            print(
                "\tBenchmarked agent was trained on "
                f"{run_stats.training_step_count} transitions over "
                f"{run_stats.training_episode_count} episodes"
            )
        print(
            f"\tMax reward over {run_stats.episode_count} episodes: "
            f"{run_stats.max_reward}"
        )
        print(
            f"\tMean reward over {run_stats.episode_count} episodes: "
            f"{run_stats.mean_reward}"
        )
        print(
            f"\tMedian reward over {run_stats.episode_count} episodes: "
            f"{run_stats.median_reward}"
        )
        print(
            f"\tMin reward over {run_stats.episode_count} episodes: "
            f"{run_stats.min_reward}"
        )
        print()

    def _get_run_stats(self, run_id=None):
        if run_id is None:
            run_id = mlflow.active_run().info.run_id
        run_data = [d for d in self.episode_data if d["active_run"] == run_id]
        episode_lengths = [d["steps"] for d in run_data]
        episode_returns = [d["reward"] for d in run_data]
        training_episodes, training_steps = self.get_training_info()
        return RunStats(
            episode_count=len(run_data),
            step_count=sum(episode_lengths),
            max_reward=max(episode_returns),
            mean_reward=statistics.mean(episode_returns),
            median_reward=statistics.median(episode_returns),
            min_reward=min(episode_returns),
            training_episode_count=training_episodes,
            training_step_count=training_steps,
        )

    def add_episode_data(self, steps: int, reward: float):
        self.episode_data.append(
            {
                "steps": steps,
                "reward": reward,
                "active_run": mlflow.active_run().info.run_id,
            }
        )

    def reset(self) -> None:
        self.start_run_type(self.RESET_KEY)


class RunContextManager:
    def __init__(
        self,
        tracker: AgentTracker,
        run_type: str,
        agent_name: Optional[str],
        environment_name: Optional[str],
    ):
        self.tracker = tracker
        self.run_type = run_type
        self.agent_name = agent_name or "agent"
        self.environment_name = environment_name or "environment"
        self._check_component_exists_in_run("agent")
        self._check_component_exists_in_run("environment")

    def _check_component_exists_in_run(self, role_type: str) -> None:
        run = mlflow.active_run()
        artifacts_dir = self.tracker._get_artifacts_dir(run)
        spec_path = artifacts_dir / "agentos.yaml"
        names = Component._get_name_map(spec_path)
        expected_name = getattr(self, f"{role_type}_name")
        if expected_name not in names:
            print(
                f"Warning: unknown {role_type.capitalize()} component: "
                f"{expected_name}.  Run will not be publishable."
            )
            self.components_exist = False
            mlflow.log_param(f"{role_type}_exists", False)
        else:
            mlflow.log_param(f"{role_type}_exists", True)

    def __enter__(self) -> None:
        self.tracker.start_run_type(self.run_type)
        self.tracker.log_agent_name(self.agent_name)
        self.tracker.log_environment_name(self.environment_name)

    def __exit__(self, type, value, traceback) -> None:
        self.tracker.log_run_metrics()
        self.tracker.print_results()
