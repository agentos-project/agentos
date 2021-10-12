from acme.tf import networks
import sonnet as snt
from pathlib import Path
import tensorflow as tf


class R2D2Network:
    def __init__(self, **kwargs):
        self.backing_dir = kwargs["backing_dir"]
        self.rnn = BasicRNN(self.environment)

    # https://github.com/deepmind/sonnet#tensorflow-checkpointing
    def save_tensorflow(self):
        checkpoint = tf.train.Checkpoint(module=self.rnn)
        checkpoint.save(Path(self.backing_dir) / "network")

    def restore_tensorflow(self):
        checkpoint = tf.train.Checkpoint(module=self.rnn)
        latest = tf.train.latest_checkpoint(self.backing_dir)
        if latest is not None:
            print("AgentOS: Restoring policy network from checkpoint")
            checkpoint.restore(latest)
        else:
            print("AgentOS: No checkpoint found for policy network")


# BasicRNN, taken from r2d2 test
# https://github.com/deepmind/acme/blob/master/acme/agents/tf/r2d2/agent_test.py
class BasicRNN(networks.RNNCore):
    def __init__(self, environment):
        super().__init__(name="basic_r2d2_RNN_network")
        self._net = snt.DeepRNN(
            [
                snt.Flatten(),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.nets.MLP(
                    [16, 16, environment.get_spec().actions.num_values]
                ),
            ]
        )

    def __call__(self, inputs, state):
        return self._net(inputs, state)

    def initial_state(self, batch_size: int, **kwargs):
        return self._net.initial_state(batch_size)

    def unroll(self, inputs, state, sequence_length):
        return snt.static_unroll(self._net, inputs, state, sequence_length)
