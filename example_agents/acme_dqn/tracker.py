import mlflow
import yaml
import tempfile
import shutil
import statistics
import tensorflow as tf
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


# Adheres to Acme Logger interface
# https://github.com/deepmind/acme/blob/master/acme/utils/loggers/base.py
class AcmeTracker:
    MLFLOW_EXPERIMENT_ID = "0"
    STEP_KEY = "steps"
    EPISODE_KEY = "episodes"
    LEARN_KEY = "learn"
    EVALUATE_KEY = "evaluate"
    RUN_TYPE_TAG = "run_type"

    def __init__(self, *args, **kwargs):
        mlflow.start_run(experiment_id=self.MLFLOW_EXPERIMENT_ID)
        self.episode_data = []
        self.evaluate_run = lambda: EvaluateRunManager(self)
        self.learn_run = lambda: LearnRunManager(self)

    # Acme logger API
    def write(self, data):
        self.episode_data.append(data)

    # Acme logger API
    def close(self):
        pass

    def start_evaluate_run(self):
        self._start_generic_run()
        mlflow.set_tag(self.RUN_TYPE_TAG, self.EVALUATE_KEY)

    def start_learn_run(self):
        self._start_generic_run()
        mlflow.set_tag(self.RUN_TYPE_TAG, self.LEARN_KEY)

    def _start_generic_run(self):
        assert mlflow.active_run() is not None
        mlflow.log_param("component_name", self.__agentos__["component_name"])
        mlflow.log_param("entry_point", self.__agentos__["entry_point"])
        mlflow.log_artifact(
            Path(self.__agentos__["component_spec_file"]).absolute()
        )
        self.log_data_artifact(
            "parameter_file", self.__agentos__["fully_qualified_params"]
        )

    def log_data_artifact(self, name, data):
        dir_path = Path(tempfile.mkdtemp())
        artifact_path = dir_path / name
        with open(artifact_path, "w") as file_out:
            file_out.write(yaml.safe_dump(data))
        mlflow.log_artifact(artifact_path)
        shutil.rmtree(dir_path)

    def log_learn_run_metrics(self):
        assert self.episode_data, "No episode data!"
        assert mlflow.active_run() is not None
        mlflow.log_param(self.EPISODE_KEY, self.episode_data[-1]["episodes"])
        mlflow.log_param(self.STEP_KEY, self.episode_data[-1]["steps"])

    def get_training_info(self):
        runs = self._get_all_runs()
        total_episodes = 0
        total_steps = 0
        for run in runs:
            if run.data.tags.get(self.RUN_TYPE_TAG) == self.LEARN_KEY:
                total_episodes += int(run.data.params.get(self.EPISODE_KEY, 0))
                total_steps += int(run.data.params.get(self.STEP_KEY, 0))
        return total_episodes, total_steps

    def _get_all_runs(self):
        assert mlflow.active_run() is not None
        run_infos = mlflow.list_run_infos(
            experiment_id=self.MLFLOW_EXPERIMENT_ID,
            order_by=["attribute.end_time DESC"],
        )
        runs = [
            mlflow.get_run(run_id=run_info.run_id) for run_info in run_infos
        ]
        return [mlflow.active_run()] + runs

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

    def save_tensorflow(self, name, network):
        assert mlflow.active_run() is not None
        dir_path = Path(tempfile.mkdtemp())
        checkpoint = tf.train.Checkpoint(module=network)
        checkpoint.save(dir_path / name / name)
        mlflow.log_artifact(dir_path / name)
        shutil.rmtree(dir_path)

    def restore_tensorflow(self, name, network):
        runs = self._get_all_runs()
        for run in runs:
            if run is None:
                continue
            artifacts_uri = run.info.artifact_uri
            if "file://" != artifacts_uri[:7]:
                raise Exception(f"Non-local artifacts path: {artifacts_uri}")
            artifacts_dir = Path(artifacts_uri[7:]).absolute()
            save_path = artifacts_dir / name
            if save_path.is_dir():

                checkpoint = tf.train.Checkpoint(module=network)
                latest = tf.train.latest_checkpoint(save_path)
                if latest is not None:
                    checkpoint.restore(latest)
                    print(f"AcmeTracker: Restored Tensorflow model {name}.")
                    return
        print(f"AcmeTracker: No saved Tensorflow model {name} found.")

    def reset(self):
        tracking_uri = mlflow.get_tracking_uri()
        mlflow.end_run()
        if "file://" != tracking_uri[:7]:
            raise Exception(f"Non-local tracking path: {tracking_uri}")
        tracking_dir = Path(tracking_uri[7:]).absolute()
        assert tracking_dir.is_dir()
        if input(f"Reset agent by removing {tracking_dir} [y/n]?  ") in [
            "y",
            "Y",
        ]:
            shutil.rmtree(tracking_dir)
            print("Agent reset")
