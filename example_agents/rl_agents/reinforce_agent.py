"""An agent that learns using the classic RL REINFORCE algorithm.

See `Sutton & Barto <http://incompleteideas.net/book/RLbook2020.pdf>`_
section 13.3, page 326.

REINFORCE, also known as Monte Carlo policy gradient, is one of the
classic Reinforcement Learing algorithms.
"""
import agentos
import numpy as np
import tensorflow as tf
from tensorflow import keras
import tensorflow_probability as tfp


class Policy:
    def __init__(self):
        self.nn = keras.Sequential(
            [
                keras.layers.Dense(4, activation="relu", input_shape=(4,)),
                keras.layers.Dense(1, activation="sigmoid"),
            ]
        )
        self.optimizer = keras.optimizers.Adam()
        self.loss_fn = keras.losses.binary_crossentropy

    def compute_action(self, obs):
        return int(round(self.nn(np.array(obs)[np.newaxis]).numpy()[0][0]))


class ReinforceAgent(agentos.Agent):
    def _init(self):
        self.ret_vals = []
        self.policy = Policy()

    def advance(self):
        self.train()
        res = agentos.rollout(self.policy, self.env.__class__, max_steps=200)
        self.ret_vals.append(sum(res.rewards))
        print(f"num steps: {self.ret_vals[-1]}")

    def train(self, num_rollouts=1, max_rollout_steps=200, discount_rate=0.9):
        grads = []
        rewards = []

        # Compute and collect grads as we take steps in our rollout.
        def rollout_step(policy, obs):
            with tf.GradientTape() as tape:
                leftprob = policy.nn(np.array(obs)[np.newaxis])
                action = (
                    tfp.distributions.Bernoulli(probs=leftprob)
                    .sample()[0][0]
                    .numpy()
                )
                loss = tf.reduce_mean(policy.loss_fn(action, leftprob))
            grads[-1].append(
                tape.gradient(loss, policy.nn.trainable_variables)
            )
            return action

        for episode_num in range(num_rollouts):
            grads.append([])
            result = agentos.rollout(
                self.policy,
                self.env.__class__,
                step_fn=rollout_step,
                max_steps=max_rollout_steps,
            )
            rewards.append(result.rewards)

        # Compute discounted normalized rewards
        d_rewards = None
        for reward_list in rewards:
            for i in range(len(reward_list) - 2, -1, -1):
                reward_list[i] += reward_list[i + 1] * discount_rate
            if d_rewards is not None:
                d_rewards = tf.concat([d_rewards, [reward_list]], axis=0)
            else:
                d_rewards = tf.ragged.constant([reward_list])

        # Normalize rewards
        avg_rewards = tf.math.reduce_mean(d_rewards, keepdims=False)
        std_rewards = tf.math.reduce_std(d_rewards.flat_values)
        normalized_rewards = (d_rewards - avg_rewards) / std_rewards

        # Weight loss function gradients by the normalized discounted rewards
        avg_weighted_grads = []
        for model_var_num in range(len(self.policy.nn.trainable_variables)):
            weighted_grads = [
                reward * grads[ep_num][st_num][model_var_num]
                for ep_num, rewards in enumerate(normalized_rewards)
                for st_num, reward in (enumerate(rewards))
            ]
            avg_weighted_grads.append(tf.reduce_mean(weighted_grads, axis=0))

        self.policy.optimizer.apply_gradients(
            zip(avg_weighted_grads, self.policy.nn.trainable_variables)
        )

    def __del__(self):
        print(
            f"Agent done!\n"
            f"Num rollouts: {len(self.ret_vals)}\n"
            f"Avg return: {np.mean(self.ret_vals)}\n"
            f"Max return: {max(self.ret_vals)}\n"
            f"Median return: {np.median(self.ret_vals)}\n"
        )


if __name__ == "__main__":
    import argparse
    from gym.envs.classic_control import CartPoleEnv

    parser = argparse.ArgumentParser(
        "Run reinforce with a simple TF policy on gym CartPole."
    )
    parser.add_argument(
        "max_agent_steps",
        metavar="MAX_AGENT_STEPS",
        help="how many steps to train on",
    )
    # TODO make the following params pass through
    # parser.add_argument("--rollouts", type=int, default=1)
    # parser.add_argument("--max_steps_per_episode", type=int, default=200)
    # parser.add_argument("--discount_rate", type=float, default=0.9)
    args = parser.parse_args()
    agentos.run_agent(
        ReinforceAgent,
        CartPoleEnv,
        max_steps=args.max_agent_steps,
    )
