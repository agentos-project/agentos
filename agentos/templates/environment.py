{file_header}
import agentos
import numpy as np
from dm_env import specs


# Simulates a 1D corridor
class Corridor(agentos.Environment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.length = 5
        self.action_space = [0, 1]
        self.observation_space = [0, 1, 2, 3, 4, 5]
        self.reset()

    def step(self, action):
        assert action in self.action_space
        if action == 0:
            self.position = np.array(
                [np.float32(max(self.position[0] - 1, 0))]
            )
        else:
            self.position = np.array(
                [np.float32(min(self.position[0] + 1, self.length))]
            )
        return (self.position, -1, self.done, {{}})

    def reset(self):
        self.position = np.array([np.float32(0)])
        return self.position

    def get_spec(self):
        observations = specs.Array(
            shape=(1,), dtype=np.dtype("float32"), name="observations"
        )
        actions = specs.DiscreteArray(num_values=2, name="actions")
        rewards = specs.Array(shape=(), dtype=np.dtype("int64"), name="reward")
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

    @property
    def valid_actions(self):
        return self.action_space

    @property
    def done(self):
        return self.position[0] >= self.length
