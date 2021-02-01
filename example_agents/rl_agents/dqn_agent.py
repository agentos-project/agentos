import agentos
import random
import tensorflow as tf
import tensorflow.keras as keras
import numpy as np
import pandas as pd
from gym.envs.classic_control import MountainCarEnv


class EpsilonGreedyTFPolicy:
    def __init__(self, env_class):
        self.action_space = env_class().action_space
        self.observation_space = env_class().observation_space
        self.model = keras.Sequential(
            [
                keras.layers.Dense(
                    16,
                    input_shape=self.observation_space.shape,
                    activation="elu",
                ),
                keras.layers.Dense(self.action_space.n),
            ]
        )
        self.optimizer = keras.optimizers.Adam(lr=0.01)
        self.age = 0

    def compute_action(self, obs):
        self.age += 1
        epsilon = min(
            0.95, 1000.0 / self.age
        )  # decay epsilon so that we can converge to Q*
        if self.age % 5000 == 0:
            print(f"compute_action #{self.age}: epsilon is %s" % epsilon)
        if (
            np.random.random() < epsilon
        ):  # with epsilon probability, act randomly.
            return self.action_space.sample()
        return np.argmax(
            self.model(obs[np.newaxis])
        )  # with 1-epsilon probability, use the policy


class LearningAgent(agentos.Agent):
    def __init__(self, env_class, policy):
        super().__init__(env_class)
        self.policy = policy

    def advance(self):
        print("training")
        self.train()
        print("evaluating")
        t = agentos.rollout(self.policy, self.env.__class__, max_steps=200)
        print(f"evaluating policy, return: {sum(t.rewards)}")

    def train(self):
        raise NotImplementedError


class DQNAgent(LearningAgent):
    def __init__(self, env_class, policy):
        super().__init__(env_class, policy)
        self.num_episodes = 50
        self.max_steps_per_episode = 200
        self.batch_size = 32
        self.num_actions = 2
        self.discount_rate = 0.95

        self.memory_buffer = pd.DataFrame(
            columns=["states", "actions", "rewards", "next_states", "dones"]
        )
        self.best_score, self.best_model = 0, None
        self.all_scores = []

    def train(self):
        for episode_num in range(self.num_episodes):
            traj = agentos.rollout(
                self.policy,
                self.env.__class__,
                max_steps=self.max_steps_per_episode,
            )

            pre_state = traj.init_obs
            for i in range(len(traj.observations)):
                self.memory_buffer.loc[len(self.memory_buffer)] = [
                    pre_state,
                    traj.actions[i],
                    traj.rewards[i],
                    traj.observations[i],
                    traj.dones[i],
                ]
                pre_state = traj.observations[i]

            ret = sum(traj.rewards)
            if ret >= self.best_score:
                print(f"Got best score while training {ret}")
                self.best_score = ret

            # let memory build up a bit before starting to iterate on the model
            if episode_num > 50:
                indices = [x for x in range(len(self.memory_buffer))]
                random.shuffle(indices)
                batch_indices = indices[: self.batch_size]
                observations = self.memory_buffer.iloc[batch_indices]
                next_per_action_q_vals = self.policy.model(
                    np.vstack(observations.next_states)
                )
                next_q_vals = np.max(next_per_action_q_vals, axis=1)
                target_q_vals = (
                    observations.rewards
                    + (1 - observations.dones)
                    * self.discount_rate
                    * next_q_vals
                )

                def loss():
                    per_action_q_vals = self.policy.model(
                        np.vstack(observations.states)
                    )
                    action_selector = tf.one_hot(
                        tf.math.argmax(per_action_q_vals, axis=1),
                        depth=2,
                        on_value=1.0,
                        off_value=0.0,
                    )
                    q_vals = tf.reduce_sum(
                        action_selector * per_action_q_vals, axis=1
                    )
                    return tf.reduce_mean(tf.square(q_vals - target_q_vals))

                self.policy.optimizer.minimize(
                    loss, self.policy.model.trainable_variables
                )


if __name__ == "__main__":
    agentos.run_agent(
        DQNAgent, MountainCarEnv, EpsilonGreedyTFPolicy(MountainCarEnv)
    )
