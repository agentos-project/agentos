import mlflow
import yaml
import tempfile
import shutil
import statistics
from pathlib import Path


class EvaluateRunManager:
    def __init__(self, tracker):
        self.tracker = tracker

    def __enter__(self):
        self.tracker.start_evaluate_run()

    def __exit__(self, type, value, traceback):
        self.tracker.print_results()


class LearnRunManager:
    def __init__(self, tracker):
        self.tracker = tracker

    def __enter__(self):
        self.tracker.start_learn_run()

    def __exit__(self, type, value, traceback):
        self.tracker.log_learn_run_metrics()
        self.tracker.print_results()


class AgentTracker:
    MLFLOW_EXPERIMENT_ID = "0"
    STEP_KEY = "steps"
    EPISODE_KEY = "episodes"
    LEARN_KEY = "learn"
    RESET_KEY = "reset"
    EVALUATE_KEY = "evaluate"
    RUN_TYPE_TAG = "run_type"

    def __init__(self, *args, **kwargs):
        mlflow.start_run(experiment_id=self.MLFLOW_EXPERIMENT_ID)
        self.episode_data = []
        self.evaluate_run = lambda: EvaluateRunManager(self)
        self.learn_run = lambda: LearnRunManager(self)

    def start_evaluate_run(self):
        self._start_generic_run()
        mlflow.set_tag(self.RUN_TYPE_TAG, self.EVALUATE_KEY)

    def start_learn_run(self):
        self._start_generic_run()
        mlflow.set_tag(self.RUN_TYPE_TAG, self.LEARN_KEY)

    def start_reset_run(self):
        self._start_generic_run()
        mlflow.set_tag(self.RUN_TYPE_TAG, self.RESET_KEY)

    def _start_generic_run(self):
        assert mlflow.active_run() is not None
        mlflow.log_param("component_name", self.__agentos__["component_name"])
        mlflow.log_param("entry_point", self.__agentos__["entry_point"])
        mlflow.log_artifact(
            Path(self.__agentos__["component_spec_file"]).absolute()
        )
        self.log_data_as_artifact(
            "parameter_file.yaml", self.__agentos__["fully_qualified_params"]
        )

    def log_data_as_artifact(self, name, data):
        dir_path = Path(tempfile.mkdtemp())
        artifact_path = dir_path / name
        with open(artifact_path, "w") as file_out:
            file_out.write(yaml.safe_dump(data))
        mlflow.log_artifact(artifact_path)
        shutil.rmtree(dir_path)

    def log_learn_run_metrics(self):
        assert self.episode_data, "No episode data!"
        assert mlflow.active_run() is not None
        data = self.episode_data[-1]
        self.log_episode_count(data["episodes"])
        self.log_step_count(data["steps"])

    def log_episode_count(self, count):
        mlflow.log_metric(self.EPISODE_KEY, count)

    def log_step_count(self, count):
        mlflow.log_metric(self.STEP_KEY, count)

    def get_training_info(self):
        runs = self._get_all_runs()
        total_episodes = 0
        total_steps = 0
        for run in runs:
            if run.data.tags.get(self.RUN_TYPE_TAG) == self.LEARN_KEY:
                total_episodes += int(
                    run.data.metrics.get(self.EPISODE_KEY, 0)
                )
                total_steps += int(run.data.metrics.get(self.STEP_KEY, 0))
        return total_episodes, total_steps

    def _get_all_runs(self, respect_reset=True):
        assert mlflow.active_run() is not None
        run_infos = mlflow.list_run_infos(
            experiment_id=self.MLFLOW_EXPERIMENT_ID,
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
        episode_lengths = [d["episode_length"] for d in self.episode_data]
        mean = statistics.mean(episode_lengths)
        median = statistics.median(episode_lengths)
        episodes, steps = self.get_training_info()
        print()
        print(f"Benchmark results after {len(episode_lengths)} episodes:")
        print(
            "\tBenchmarked agent was trained on "
            f"{steps} transitions over {episodes} episodes"
        )
        print(
            f"\tMax steps over {len(episode_lengths)} trials: "
            f"{max(episode_lengths)}"
        )
        print(f"\tMean steps over {len(episode_lengths)} trials: {mean}")
        print(f"\tMedian steps over {len(episode_lengths)} trials: {median}")
        print(
            f"\tMin steps over {len(episode_lengths)} trials: "
            f"{min(episode_lengths)}"
        )
        print()

    def reset(self):
        self.start_reset_run()
