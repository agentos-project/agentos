"""An agent that makes random decisions using a TensorFlow policy."

This agent creates and uses a new randomly initialized
TensorFlow NN policy for each step but doesn't do any
learning.
"""
import agentos
from tensorflow import keras
import numpy as np


class Policy:
    def __init__(self):
        self.nn = keras.Sequential(
            [
                keras.layers.Dense(
                    4, activation="relu", input_shape=(4,), dtype="float64"
                ),
                keras.layers.Dense(1, activation="sigmoid", dtype="float64"),
            ]
        )

    def compute_action(self, obs):
        return int(round(self.nn(np.array(obs)[np.newaxis]).numpy()[0][0]))


class RandomTFAgent(agentos.Agent):
    def _init(self):
        self.ret_vals = []

    def advance(self):
        ret = sum(self.evaluate_policy(Policy(), max_steps=2000))
        self.ret_vals.append(ret)

    def __del__(self):
        print(
            f"Agent done!\n"
            f"Num rollouts: {len(self.ret_vals)}\n"
            f"Avg return: {np.mean(self.ret_vals)}\n"
            f"Max return: {max(self.ret_vals)}\n"
            f"Median return: {np.median(self.ret_vals)}\n"
        )


if __name__ == "__main__":
    from gym.envs.classic_control import CartPoleEnv

    agentos.run_agent(RandomTFAgent, CartPoleEnv, max_iters=5)
