import shutil
import sonnet as snt
import tempfile
import tensorflow as tf
from pathlib import Path
from agentos.run import Run


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
        dir_path = Path(tempfile.mkdtemp())
        checkpoint = tf.train.Checkpoint(module=self.net)
        checkpoint.save(dir_path / self.save_as_name / self.save_as_name)
        if run:
            run.log_artifact(dir_path / self.save_as_name)
        shutil.rmtree(dir_path)

    def restore(self):
        runs = Run.get_all_runs()
        for run in runs:
            save_path = run.download_artifacts(self.save_as_name)
            if save_path.is_dir():
                checkpoint = tf.train.Checkpoint(module=self.net)
                latest = tf.train.latest_checkpoint(save_path)
                if latest is not None:
                    checkpoint.restore(latest)
                    self.save_tensorflow()
                    print(
                        f"AcmeRunManager: Restored Tensorflow model "
                        f"{self.save_as_name}."
                    )
                    return
        self.save_tensorflow()
        print(
            f"AcmeRunManager: No saved Tensorflow model "
            f"{self.save_as_name} found."
        )
