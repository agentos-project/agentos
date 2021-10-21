import mlflow
import tempfile
import shutil
import tensorflow as tf
from pathlib import Path
from agentos.tracker import BaseTracker


# Adheres to Acme Logger interface
# https://github.com/deepmind/acme/blob/master/acme/utils/loggers/base.py
class AcmeTracker(BaseTracker):
    # Acme logger API
    def write(self, data):
        self.episode_data.append(data)

    # Acme logger API
    def close(self):
        pass

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
