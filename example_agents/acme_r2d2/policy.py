import numpy as np
import sonnet as snt
import trfl
from acme.agents.tf import actors
from acme.tf import utils as tf2_utils


class R2D2Policy:
    def __init__(self, **kwargs):
        self.epsilon = kwargs["epsilon"]
        self.store_lstm_state = kwargs["store_lstm_state"]
        self.network.restore()
        tf2_utils.create_variables(
            self.network.rnn, [self.environment.get_spec().observations]
        )

        def epsilon_greedy_fn(qs):
            return trfl.epsilon_greedy(qs, epsilon=self.epsilon).sample()

        policy_network = snt.DeepRNN([self.network.rnn, epsilon_greedy_fn])
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
