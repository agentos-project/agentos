import tensorflow as tf
import sonnet as snt
from pathlib import Path


class AcmeDQNNetwork:
    def __init__(self, **kwargs):
        self.backing_dir = kwargs["backing_dir"]
        self.net = snt.Sequential(
            [
                snt.Flatten(),
                snt.nets.MLP(
                    [50, 50, self.environment.get_spec().actions.num_values]
                ),
            ]
        )
        self.restore_tensorflow()

    def save_tensorflow(self):
        checkpoint = tf.train.Checkpoint(self.net)
        checkpoint.save(Path(self.backing_dir) / "dqn_network")

    def restore_tensorflow(self):
        checkpoint = tf.train.Checkpoint(self.net)
        latest = tf.train.latest_checkpoint(self.backing_dir)
        if latest is not None:
            print("AgentOS: Restoring backing network from checkpoint")
            checkpoint.restore(latest)
        else:
            print("AgentOS: No checkpoint found for backing network")
