"""Implementation of agents available in AgentOS. See core.py for Agent API."""
from agentos import Agent
import ray
import ray.rllib.agents.registry as rllib_registry
from ray.tune.registry import register_env as rllib_reg_env



class RandomAgent(Agent):
    def step(self):
        obs, reward, done, _ = self.env.step(self.env.action_space.sample())
        return done


class RLlibAgent(Agent):
    def __init__(self, env_class, algo_name, rllib_config=None):
        """Init a Ray agent with the given env_class and an algorithm name.

        :param algo_name: A string. For valid values of algo_name, see
        https://github.com/ray-project/ray/blob/master/rllib/agents/registry.py
        """
        super().__init__(env_class)
        if not ray.is_initialized():
            ray.init()
        trainer_class = rllib_registry._get_agent_class(algo_name)
        print(type(trainer_class))
        def wrapper(conf): return env_class()  # Ray requires env.__init__ take config.
        rllib_reg_env(env_class.__name__, wrapper)
        self.ray_trainer = trainer_class(config=rllib_config, env=env_class.__name__)
        self._last_obs = self.init_obs

    def step(self):
        action = self.ray_trainer.compute_action(self._last_obs)
        self._last_obs, _, done, _ = self.env.step(action)
        return done

    def train(self, num_iterations):
        """Causes Ray to learn"""
        self.ray_agent.train(num_iterations)

