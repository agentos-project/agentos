import mlflow
import tempfile
import shutil
import tensorflow as tf
from pathlib import Path
from agentos.tracker import AgentTracker


# Adheres to Acme Logger interface
# https://github.com/deepmind/acme/blob/master/acme/utils/loggers/base.py
class AcmeTracker(AgentTracker):
    # Acme logger API
    def write(self, data: dict):
        self.add_episode_data(
            steps=data["episode_length"],
            reward=data["episode_return"].item(),
        )

    # Acme logger API
    def close(self):
        pass

    def save_tensorflow(self, name: str, network: tf.Module):
        assert mlflow.active_run() is not None
        dir_path = Path(tempfile.mkdtemp())
        checkpoint = tf.train.Checkpoint(module=network)
        checkpoint.save(dir_path / name / name)
        mlflow.log_artifact(dir_path / name)
        shutil.rmtree(dir_path)

    def restore_tensorflow(self, name: str, network: tf.Module) -> None:
        runs = self._get_all_runs()
        for run in runs:
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
                    self.save_tensorflow(name, network)
                    print(f"AcmeTracker: Restored Tensorflow model {name}.")
                    return
        self.save_tensorflow(name, network)
        print(f"AcmeTracker: No saved Tensorflow model {name} found.")
