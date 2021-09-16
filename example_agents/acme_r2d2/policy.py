from acme import specs
from acme.agents.tf import actors
from acme.tf import networks
from acme.tf import utils as tf2_utils
import trfl
import numpy as np
import sonnet as snt
import agentos


# BasicRNN, taken from r2d2 test
# https://github.com/deepmind/acme/blob/master/acme/agents/tf/r2d2/agent_test.py
class BasicRNN(networks.RNNCore):
    def __init__(self, action_spec: specs.DiscreteArray):
        super().__init__(name="basic_r2d2_RNN_network")
        self._net = snt.DeepRNN(
            [
                snt.Flatten(),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.VanillaRNN(16),
                snt.nets.MLP([16, 16, action_spec.num_values]),
            ]
        )

    def __call__(self, inputs, state):
        return self._net(inputs, state)

    def initial_state(self, batch_size: int, **kwargs):
        return self._net.initial_state(batch_size)

    def unroll(self, inputs, state, sequence_length):
        return snt.static_unroll(self._net, inputs, state, sequence_length)


class R2D2Policy(agentos.Policy):
    @classmethod
    def ready_to_initialize(cls, shared_data):
        return "environment_spec" in shared_data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        environment_spec = self.shared_data["environment_spec"]
        network = BasicRNN(environment_spec.actions)
        agentos.restore_tensorflow("network", network)
        self.shared_data["network"] = network
        tf2_utils.create_variables(network, [environment_spec.observations])

        def epsilon_greedy_fn(qs):
            return trfl.epsilon_greedy(
                qs, epsilon=agentos.parameters.epsilon
            ).sample()

        policy_network = snt.DeepRNN(
            [
                network,
                epsilon_greedy_fn,
            ]
        )
        ADDER = None
        self.actor = actors.RecurrentActor(
            policy_network,
            ADDER,
            store_recurrent_state=agentos.parameters.store_lstm_state,
        )

    def decide(self, observation, actions, should_learn=False):
        # TODO - ugly typing
        if not isinstance(observation, type(np.array)):
            observation = np.array(observation)
        if observation.dtype != np.zeros(1, dtype="float32").dtype:
            observation = np.float32(observation)
        action = self.actor.select_action(observation)
        self.shared_data["_prev_state"] = self.actor._prev_state
        return action
