# Thin wrapper around cartpole from OpenAI's Gym toolkit
# This env models a cart with a pole balancing on top of it
import agentos
import gym
from dm_env import specs
import numpy as np


class CartPole(agentos.Environment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cartpole = gym.make("CartPole-v1")
        self.reset()

    def step(self, action):
        assert action in [0, 1]
        result = self.cartpole.step(action)
        self.last_obs, self.last_reward, self.done, self.info = result
        # FIXME - this cast makes it match spec
        return (
            np.float32(self.last_obs),
            np.float32(self.last_reward),
            self.done,
            self.info,
        )

    @property
    def valid_actions(self):
        return [0, 1]

    def reset(self):
        self.last_obs = None
        self.last_reward = None
        self.last_done = False
        self.last_info = None
        self.last_obs = self.cartpole.reset()
        # FIXME - this cast makes it match spec
        return np.float32(self.last_obs)

    def get_spec(self):
        observations = specs.BoundedArray(
            shape=(4,),
            dtype=np.dtype("float32"),
            name="observation",
            minimum=[
                -4.8000002e00,
                -3.4028235e38,
                -4.1887903e-01,
                -3.4028235e38,
            ],
            maximum=[4.8000002e00, 3.4028235e38, 4.1887903e-01, 3.4028235e38],
        )
        actions = specs.DiscreteArray(num_values=2)
        rewards = specs.Array(
            shape=(), dtype=np.dtype("float32"), name="reward"
        )
        discounts = specs.BoundedArray(
            shape=(),
            dtype=np.dtype("float32"),
            name="discount",
            minimum=0.0,
            maximum=1.0,
        )
        return agentos.EnvironmentSpec(
            observations=observations,
            actions=actions,
            rewards=rewards,
            discounts=discounts,
        )


# Unit test for Cartpole
def run_tests():
    print("Testing Cartpole...")
    env = CartPole(shared_data={})
    spec = env.get_spec()
    assert spec is not None
    assert spec.observations is not None
    assert spec.actions is not None
    assert spec.rewards is not None
    assert spec.discounts is not None
    first_obs = env.reset()
    assert len(first_obs) == 4
    obs, reward, done, info = env.step(0)
    obs, reward, done, info = env.step(1)
    while not done:
        obs, reward, done, info = env.step(1)
    print("Test successful...")


if __name__ == "__main__":
    run_tests()
