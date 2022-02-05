import shutil
import sonnet as snt
import tempfile
import tensorflow as tf
from pathlib import Path
from agentos.run import Run


class TFModelSaver:
    """
    Handles saving and restoring TF models to/from Runs.
    Can be used by different network components.
    """
    @staticmethod
    def save(save_as_name: str, network: tf.Module, run=None):
        dir_path = Path(tempfile.mkdtemp())
        checkpoint = tf.train.Checkpoint(module=network)
        checkpoint.save(dir_path / save_as_name / save_as_name)
        if run:
            run.log_artifact(dir_path / save_as_name)
        shutil.rmtree(dir_path)

    @staticmethod
    def restore(save_as_name: str, network: tf.Module):
        runs = Run.get_all_runs()
        for run in runs:
            try:
                save_path = Path(run.download_artifacts(save_as_name))
                if save_path.is_dir():
                    checkpoint = tf.train.Checkpoint(module=network)
                    latest = tf.train.latest_checkpoint(save_path)
                    if latest is not None:
                        checkpoint.restore(latest)
                        print(
                            f"AcmeRunManager: Restored Tensorflow model "
                            f"{save_as_name}."
                        )
                        return
            except IOError as e:
                print(f"failed to download artifacts: {e}")
        print(
            f"AcmeRunManager: No saved Tensorflow model "
            f"{save_as_name} found."
        )


class AcmeDQNNetwork:
    def __init__(self):
        self.net = snt.Sequential(
            [
                snt.Flatten(),
                snt.nets.MLP(
                    [50, 50, self.environment.get_spec().actions.num_values]
                ),
            ]
        )
        self.save_as_name = "network"
        self.restore()

    def save(self, run=None):
        TFModelSaver.save(self.save_as_name, self.net, run=run)

    def restore(self):
        TFModelSaver.restore(self.save_as_name, self.net)
