import sonnet as snt
from acme.tf import networks


class R2D2Network:
    def __init__(self, environment, TFModelSaver):
        self.environment = environment
        self.TFModelSaver = TFModelSaver
        self.rnn = BasicRNN(self.environment)

    def save(self, run=None):
        # This attribute is set up by AgentOS
        self.TFModelSaver.save("rnn", self.rnn, run=run)

    def restore(self):
        # This attribute is set up by AgentOS
        self.TFModelSaver.restore("rnn", self.rnn)


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
