# TODO - update reqs
import agentos
from acme import datasets
import tensorflow as tf
from acme.tf import utils as tf2_utils
from acme.adders import reverb as adders
import reverb
import numpy as np
from dm_env import TimeStep
from dm_env import StepType


class ReverbDataset(agentos.Dataset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init(self, **params):
        self.parameters = params
        initial_state = self.network.initial_state(1)
        extra_spec = {
            "core_state": tf2_utils.squeeze_batch_dim(initial_state),
        }
        self.num_observations = 0
        replay_table = reverb.Table(
            name=adders.DEFAULT_PRIORITY_TABLE,
            sampler=reverb.selectors.Prioritized(self.parameters["priority_exponent"]),
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

        # Component to add things into replay.
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
            self.parameters.max_priority_weight * max_priority
            + (1 - self.parameters.max_priority_weight) * mean_priority
        )

        # Compute priorities and add an op to update them on the reverb
        # side.
        self.tf_client.update_priorities(
            table=adders.DEFAULT_PRIORITY_TABLE,
            keys=keys,
            priorities=tf.cast(priorities, tf.float64),
        )

    # https://github.com/deepmind/acme/blob/master/acme/agents/tf/actors.py#L164
    def add(self, prev_obs, action, curr_obs, reward, done, info):
        if action is None:  # No action -> first step
            timestep = TimeStep(StepType.FIRST, None, None, curr_obs)
            self.adder.add_first(timestep)
        else:
            if done:
                timestep = TimeStep(
                    StepType.LAST,
                    reward,
                    np.float32(self.parameters["discount"]),
                    curr_obs,
                )
            else:
                timestep = TimeStep(
                    StepType.MID,
                    reward,
                    np.float32(self.parameters["discount"]),
                    curr_obs,
                )

            # FIXME - hacky way to push observation counts
            if not hasattr(self, "num_observations"):
                self.num_observations = 0
            self.num_observations += 1

            # FIXME - hacky way to push recurrent state
            if self.prev_state is not None:
                numpy_state = tf2_utils.to_numpy_squeeze(
                    self.prev_state
                )
                self.adder.add(action, timestep, extras=(numpy_state,))

            else:
                # self.adder.add(action, timestep)
                raise Exception("Recurrent state not available")
