# TODO - update requirements.txt
# See acme/agents/tf/r2d2/learning.py for original code source
import copy
import functools
import agentos
import tree
from agentos import parameters
from acme.tf import utils as tf2_utils
from acme.tf import losses
from acme.tf import networks
import sonnet as snt
import tensorflow as tf


class R2D2Trainer(agentos.Trainer):
    @classmethod
    def ready_to_initialize(cls, shared_data):
        return (
            "environment_spec" in shared_data
            and "network" in shared_data
            # and "dataset_address" in shared_data
            # and "dataset" in shared_data
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.network = self.shared_data["network"]
        self.target_network = copy.deepcopy(self.network)
        self.optimizer = snt.optimizers.Adam(
            parameters.learning_rate, parameters.adam_epsilon
        )
        self.environment_spec = self.shared_data["environment_spec"]
        tf2_utils.create_variables(
            self.target_network, [self.environment_spec.observations]
        )
        self.num_steps = tf.Variable(
            0.0, dtype=tf.float32, trainable=False, name="step"
        )

        if not isinstance(self.network, networks.RNNCore):
            self.network.unroll = functools.partial(
                snt.static_unroll, self.network
            )
            self.target_network.unroll = functools.partial(
                snt.static_unroll, self.target_network
            )

    def improve(self, dataset, policy):
        num_steps = self._get_update_step_count()
        for _ in range(num_steps):
            # Run learner steps (usually means gradient steps).
            self._improve(dataset, policy)
        if num_steps > 0:
            # Update the actor weights when learner updates.
            # FIXME - I think actor update is only needed in distributed case
            # because the network is shared between the actor and the learner.
            # self.actor.update()
            pass
        agentos.save_tensorflow("network", self.shared_data["network"])

    @tf.function
    def _improve(self, dataset, policy):
        # Draw a batch of data from replay.
        sample = dataset.next()

        data = tf2_utils.batch_to_sequence(sample.data)
        observations, actions, rewards, discounts, extra = (
            data.observation,
            data.action,
            data.reward,
            data.discount,
            data.extras,
        )
        unused_sequence_length, batch_size = actions.shape

        # Get initial state for the LSTM, either from replay or use zeros.
        if parameters.store_lstm_state:
            core_state = tree.map_structure(
                lambda x: x[0], extra["core_state"]
            )
        else:
            core_state = self.network.initial_state(batch_size)
        target_core_state = tree.map_structure(tf.identity, core_state)

        # Before training, optionally unroll LSTM for a fixed warmup period.
        burn_in_length = parameters.burn_in_length
        burn_in_obs = tree.map_structure(
            lambda x: x[:burn_in_length], observations
        )
        _, core_state = self._burn_in(burn_in_obs, core_state)
        _, target_core_state = self._burn_in(burn_in_obs, target_core_state)

        # Don't train on the warmup period.
        observations, actions, rewards, discounts, extra = tree.map_structure(
            lambda x: x[burn_in_length:],
            (observations, actions, rewards, discounts, extra),
        )

        with tf.GradientTape() as tape:
            # Unroll the online and target Q-networks on the sequences.
            q_values, _ = self.network.unroll(
                observations, core_state, parameters.sequence_length
            )
            target_q_values, _ = self.target_network.unroll(
                observations, target_core_state, parameters.sequence_length
            )

            # Compute the target policy distribution (greedy).
            greedy_actions = tf.argmax(q_values, output_type=tf.int32, axis=-1)
            target_policy_probs = tf.one_hot(
                greedy_actions,
                depth=self.environment_spec.actions.num_values,
                dtype=q_values.dtype,
            )

            # Compute the transformed n-step loss.
            rewards = tree.map_structure(lambda x: x[:-1], rewards)
            discounts = tree.map_structure(lambda x: x[:-1], discounts)
            loss, extra = losses.transformed_n_step_loss(
                qs=q_values,
                targnet_qs=target_q_values,
                actions=actions,
                rewards=rewards,
                pcontinues=discounts * parameters.discount,
                target_policy_probs=target_policy_probs,
                bootstrap_n=parameters.n_step,
            )

            # Calculate importance weights and use them to scale the loss.
            sample_info = sample.info
            keys, probs = sample_info.key, sample_info.probability
            importance_weights = 1.0 / (
                parameters.max_replay_size * probs
            )  # [T, B]
            importance_weights **= parameters.importance_sampling_exponent
            importance_weights /= tf.reduce_max(importance_weights)
            loss *= tf.cast(importance_weights, tf.float32)  # [T, B]
            loss = tf.reduce_mean(loss)  # []

        # Apply gradients via optimizer.
        gradients = tape.gradient(loss, self.network.trainable_variables)
        # Clip and apply gradients.
        if parameters.clip_grad_norm is not None:
            gradients, _ = tf.clip_by_global_norm(
                gradients, parameters.clip_grad_norm
            )

        self.optimizer.apply(gradients, self.network.trainable_variables)

        # Periodically update the target network.
        if tf.math.mod(self.num_steps, parameters.target_update_period) == 0:
            for src, dest in zip(
                self.network.variables, self.target_network.variables
            ):
                dest.assign(src)
        self.num_steps.assign_add(1)

        # FIXME - ugly duck typing and custom API
        if hasattr(dataset, "update_priorities"):
            dataset.update_priorities(extra, keys)

        return {"loss": loss}

    def _burn_in(self, burn_in_obs, core_state):
        if parameters.burn_in_length:
            return self.network.unroll(
                burn_in_obs, core_state, parameters.burn_in_length
            )
        return (burn_in_obs, core_state)

    def _get_update_step_count(self):
        # ======================
        # improve the R2D2 agent.
        # code from:
        #   * acme/agents/agent.py
        #   * acme/agents/tf/r2d2/agent.py
        # ======================
        observations_per_step = (
            float(parameters.replay_period * parameters.batch_size)
            / parameters.samples_per_insert
        )
        min_observations = parameters.replay_period * max(
            parameters.batch_size, parameters.min_replay_size
        )
        num_observations = self.shared_data["num_observations"]

        num_steps = 0
        n = num_observations - min_observations
        if n < 0:
            # Do not do any learner steps until you have seen min_observations.
            num_steps = 0
        elif observations_per_step > 1:
            # One batch every 1/obs_per_step observations, otherwise zero.
            num_steps = int(n % int(observations_per_step) == 0)
        else:
            # Always return 1/obs_per_step batches every observation.
            num_steps = int(1 / observations_per_step)
        return num_steps
