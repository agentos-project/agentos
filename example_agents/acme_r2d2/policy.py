from acme.agents.tf import actors
from acme.tf import networks
from acme.tf import utils as tf2_utils
import trfl
import numpy as np
import sonnet as snt
from pathlib import Path


# BasicRNN, taken from r2d2 test
# https://github.com/deepmind/acme/blob/master/acme/agents/tf/r2d2/agent_test.py
class BasicRNN(networks.RNNCore):
    def __init__(self):
        super().__init__(name="basic_r2d2_RNN_network")

    def init(self, backing_dir):
        self.backing_dir = backing_dir
        self._net = snt.DeepRNN(
            [
                snt.Flatten(),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.nets.MLP(
                    [16, 16, self.environment.get_spec().actions.num_values]
                ),
            ]
        )

    def __call__(self, inputs, state):
        return self._net(inputs, state)

    def initial_state(self, batch_size: int, **kwargs):
        return self._net.initial_state(batch_size)

    def unroll(self, inputs, state, sequence_length):
        return snt.static_unroll(self._net, inputs, state, sequence_length)

    # https://github.com/deepmind/sonnet#tensorflow-checkpointing
    # TODO - custom saver/restorer functions
    # TODO - ONLY works for the demo (Acme on TF) because the dynamic module
    #        loading in ACR core breaks pickle. Need to figure out a more
    #        general way to handle this
    def save_tensorflow(self):
        import tensorflow as tf

        checkpoint = tf.train.Checkpoint(module=self)
        checkpoint.save(Path(self.backing_dir) / "network")

    # https://github.com/deepmind/sonnet#tensorflow-checkpointing
    # Same caveats as save_tensorflow above
    def restore_tensorflow(self):
        import tensorflow as tf

        checkpoint = tf.train.Checkpoint(module=self)
        latest = tf.train.latest_checkpoint(self.backing_dir)
        if latest is not None:
            print("AgentOS: Restoring policy network from checkpoint")
            checkpoint.restore(latest)
        else:
            print("AgentOS: No checkpoint found for policy network")


class R2D2Policy:
    def init(self, epsilon, store_lstm_state):
        self.epsilon = epsilon
        self.store_lstm_state = store_lstm_state
        self.network.restore_tensorflow()
        tf2_utils.create_variables(
            self.network, [self.environment.get_spec().observations]
        )

        def epsilon_greedy_fn(qs):
            return trfl.epsilon_greedy(qs, epsilon=self.epsilon).sample()

        policy_network = snt.DeepRNN([self.network, epsilon_greedy_fn])
        ADDER = None
        self.actor = actors.RecurrentActor(
            policy_network,
            ADDER,
            store_recurrent_state=self.store_lstm_state,
        )

    def decide(self, observation):
        # TODO - ugly typing
        if not isinstance(observation, type(np.array)):
            observation = np.array(observation)
        if observation.dtype != np.zeros(1, dtype="float32").dtype:
            observation = np.float32(observation)
        action = self.actor.select_action(observation)
        self.dataset.prev_state = self.actor._prev_state
        return action
