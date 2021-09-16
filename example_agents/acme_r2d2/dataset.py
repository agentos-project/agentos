# TODO - update reqs
import agentos
from agentos import parameters
from acme import datasets
import tensorflow as tf
from acme.tf import utils as tf2_utils
from acme.adders import reverb as adders
import reverb
import numpy as np
from dm_env import TimeStep
from dm_env import StepType


class ReverbDataset(agentos.Dataset):
    @classmethod
    def ready_to_initialize(cls, shared_data):
        return "environment_spec" in shared_data and "network" in shared_data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        initial_state = self.shared_data["network"].initial_state(1)
        extra_spec = {
            "core_state": tf2_utils.squeeze_batch_dim(initial_state),
        }
        replay_table = reverb.Table(
            name=adders.DEFAULT_PRIORITY_TABLE,
            sampler=reverb.selectors.Prioritized(parameters.priority_exponent),
            remover=reverb.selectors.Fifo(),
            max_size=parameters.max_replay_size,
            rate_limiter=reverb.rate_limiters.MinSize(min_size_to_sample=1),
            signature=adders.SequenceAdder.signature(
                self.shared_data["environment_spec"],
                extra_spec,
                sequence_length=parameters.sequence_length,
            ),
        )

        # NB - must save ref to server or it gets killed
        self.reverb_server = reverb.Server([replay_table], port=None)
        address = f"localhost:{self.reverb_server.port}"

        # Component to add things into replay.
        self.adder = adders.SequenceAdder(
            client=reverb.Client(address),
            period=parameters.replay_period,
            sequence_length=parameters.sequence_length,
        )

        self.tf_client = reverb.TFClient(address)

        # The dataset object to learn from.
        dataset = datasets.make_reverb_dataset(
            server_address=address,
            batch_size=parameters.batch_size,
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
            parameters.max_priority_weight * max_priority
            + (1 - parameters.max_priority_weight) * mean_priority
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
                    np.float32(parameters.discount),
                    curr_obs,
                )
            else:
                timestep = TimeStep(
                    StepType.MID,
                    reward,
                    np.float32(parameters.discount),
                    curr_obs,
                )

            # FIXME - hacky way to push observation counts
            if "num_observations" not in self.shared_data:
                self.shared_data["num_observations"] = 0
            self.shared_data["num_observations"] += 1

            # FIXME - hacky way to push recurrent state
            if self.shared_data["_prev_state"] is not None:
                numpy_state = tf2_utils.to_numpy_squeeze(
                    self.shared_data["_prev_state"]
                )
                self.adder.add(action, timestep, extras=(numpy_state,))

            else:
                # self.adder.add(action, timestep)
                raise Exception("Recurrent state not available")
