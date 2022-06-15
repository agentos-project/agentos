# TODO - update reqs
import reverb
import tensorflow as tf
from acme import datasets
from acme.adders import reverb as adders
from acme.tf import utils as tf2_utils

import agentos


class ReverbDataset(agentos.Dataset):
    def __init__(self, environment, network, **kwargs):
        self.environment = environment
        self.network = network
        # Could use super().__init__(**kwargs) since is a MemberInitializer.
        self.parameters = kwargs
        initial_state = self.network.rnn.initial_state(1)
        extra_spec = {
            "core_state": tf2_utils.squeeze_batch_dim(initial_state),
        }
        self.num_observations = 0
        replay_table = reverb.Table(
            name=adders.DEFAULT_PRIORITY_TABLE,
            sampler=reverb.selectors.Prioritized(
                self.parameters["priority_exponent"]
            ),
            remover=reverb.selectors.Fifo(),
            max_size=self.parameters["max_replay_size"],
            rate_limiter=reverb.rate_limiters.MinSize(min_size_to_sample=1),
            signature=adders.SequenceAdder.signature(
                self.environment.get_spec(),
                extra_spec,
                sequence_length=self.parameters["sequence_length"],
            ),
        )

        # NB - must save ref to server or it gets killed
        self.reverb_server = reverb.Server([replay_table], port=None)
        address = f"localhost:{self.reverb_server.port}"

        # Module to add things into replay.
        self.adder = adders.SequenceAdder(
            client=reverb.Client(address),
            period=self.parameters["replay_period"],
            sequence_length=self.parameters["sequence_length"],
        )

        self.tf_client = reverb.TFClient(address)

        # The dataset object to learn from.
        dataset = datasets.make_reverb_dataset(
            server_address=address,
            batch_size=self.parameters["batch_size"],
            prefetch_size=tf.data.experimental.AUTOTUNE,
        )
        self.iterator = iter(dataset)

    def next(self, *args, **kwargs):
        return next(self.iterator)

    def update_priorities(self, extra, keys):
        # Updated priorities are a mixture of max and mean sequence errors
        abs_errors = tf.abs(extra.errors)
        mean_priority = tf.reduce_mean(abs_errors, axis=0)
        max_priority = tf.reduce_max(abs_errors, axis=0)
        priorities = (
            self.parameters["max_priority_weight"] * max_priority
            + (1 - self.parameters["max_priority_weight"]) * mean_priority
        )

        # Compute priorities and add an op to update them on the reverb
        # side.
        self.tf_client.update_priorities(
            table=adders.DEFAULT_PRIORITY_TABLE,
            keys=keys,
            priorities=tf.cast(priorities, tf.float64),
        )

    def add_first(self, timestep):
        self.adder.add_first(timestep)

    def add(self, action, timestep):
        self.num_observations += 1
        assert self.prev_state is not None, "Recurrent state not available!"
        numpy_state = tf2_utils.to_numpy_squeeze(self.prev_state)
        self.adder.add(action, timestep, extras=(numpy_state,))
