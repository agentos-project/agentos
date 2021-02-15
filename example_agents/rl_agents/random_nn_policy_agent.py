"""An agent that makes random decisions using a TensorFlow policy."

This agent creates and uses a new randomly initialized
TensorFlow NN policy for each step but doesn't do any
learning.
"""
import agentos
from tensorflow import keras
import numpy as np


class SimpleTFPolicy(agentos.Policy):
    def __init__(self):
        self.nn = keras.Sequential(
            [
                keras.layers.Dense(
                    4, activation="relu", input_shape=(4,), dtype="float64"
                ),
                keras.layers.Dense(1, activation="sigmoid", dtype="float64"),
            ]
        )

    def decide(self, obs):
        return int(round(self.nn(np.array(obs)[np.newaxis]).numpy()[0][0]))


class RandomTFAgent(agentos.Agent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ret_vals = []

    def advance(self):
        trajs = agentos.rollout(
            SimpleTFPolicy(),
            self.environment,
            max_steps=2000
        )
        self.ret_vals.append(sum(trajs.rewards))


if __name__ == "__main__":
    from gym.envs.classic_control import CartPoleEnv

    random_nn_agent = RandomTFAgent(
        environment=CartPoleEnv,
        policy=SimpleTFPolicy,
    )
    agentos.run_agent(random_nn_agent, max_iters=10)
    print(
        f"Agent done!\n"
        f"Num rollouts: {len(random_nn_agent.ret_vals)}\n"
        f"Avg return: {np.mean(random_nn_agent.ret_vals)}\n"
        f"Max return: {max(random_nn_agent.ret_vals)}\n"
        f"Median return: {np.median(random_nn_agent.ret_vals)}\n"
    )
