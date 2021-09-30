"""An agent that makes random decisions using a TensorFlow policy."

This agent creates and uses a new randomly initialized
TensorFlow NN policy for each step but doesn't do any
learning.
"""
import agentos
from tensorflow import keras
import numpy as np


class SingleLayerTFPolicy(agentos.Policy):
    def __init__(self, action_space, observation_space, num_nodes=4):
        self.action_space = action_space
        print(f"set self.action_space.n {self.action_space.n}")
        self.observation_space = observation_space
        assert self.action_space.n == 2
        self.nn = keras.Sequential(
            [
                keras.layers.Dense(
                    num_nodes,
                    activation="relu",
                    input_shape=self.observation_space.shape,
                ),
                keras.layers.Dense(1),
            ]
        )

    def decide(self, obs):
        return int(
            max(0, round(self.nn(np.array(obs)[np.newaxis]).numpy()[0][0]))
        )


class RandomTFAgent(agentos.Agent):
    def __init__(self, environment, policy):
        super().__init__(environment=environment, policy=policy)
        self.ret_vals = []

    def advance(self):
        trajs = agentos.rollout(self.policy, self.environment, max_steps=2000)
        self.ret_vals.append(sum(trajs.rewards))


if __name__ == "__main__":
    from gym.envs.classic_control import CartPoleEnv

    random_nn_agent = RandomTFAgent(
        environment=CartPoleEnv,
        policy=SingleLayerTFPolicy(
            CartPoleEnv().action_space, CartPoleEnv().observation_space,
        ),
    )
    agentos.run_component(random_nn_agent, max_iters=10)
    print(
        f"Agent done!\n"
        f"Num rollouts: {len(random_nn_agent.ret_vals)}\n"
        f"Avg return: {np.mean(random_nn_agent.ret_vals)}\n"
        f"Max return: {max(random_nn_agent.ret_vals)}\n"
        f"Median return: {np.median(random_nn_agent.ret_vals)}\n"
    )
