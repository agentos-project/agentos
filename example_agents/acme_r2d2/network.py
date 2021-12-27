from acme.tf import networks
import sonnet as snt


class R2D2Network:
    def __init__(self):
        self.rnn = BasicRNN(self.environment)

    def restore(self):
        self.AcmeRun.restore_tensorflow("rnn", self.rnn)

    def save(self):
        self.AcmeRun.save_tensorflow("rnn", self.rnn)


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
