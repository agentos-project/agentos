import ray
import ray.rllib.agents.registry as rllib_registry
from ray.tune.registry import register_env as rllib_reg_env
from ray.rllib.agents.trainer import COMMON_CONFIG

class RLlibAgent:
    def init(self,
             algo_name="PPO",
             trainer_config=COMMON_CONFIG):
        """Init a Ray agent with the given env_class and an algorithm name.

        :param algo_name: A string. For valid values of algo_name, see
        https://github.com/ray-project/ray/blob/master/rllib/agents/registry.py
        """
        env_class = self.env.unwrapped.__class__
        if not ray.is_initialized():
            ray.init()
        trainer_class = rllib_registry.get_trainer_class(algo_name)
        print()
        print(type(trainer_class))

        def wrapper(conf):
            return env_class()  # Ray requires env.__init__() take config.

        rllib_reg_env(env_class.__name__, wrapper)
        self.ray_trainer = trainer_class(
            config=self.trainer_config, env=env_class.__name__
        )
        self._last_obs = self.init_obs
        self.done = False

    def evaluate(self):
        if self.done:
            return True
        action = self.ray_trainer.compute_action(self._last_obs)
        self._last_obs, _, self.done, _ = self.env.step(action)
        return self.done

    def train(self, num_iterations):
        """Causes Ray to learn"""
        self.ray_agent.train(num_iterations)


def test_rllib_agent():
    from gym.envs.classic_control import CartPoleEnv

    agent = RLlibAgent(CartPoleEnv, "PPO")
    done = agent.advance()
    assert not done, "CartPole should not finish after one random step."
    agent.train(1)
    while not done:
        print("stepping agent")
        done = agent.advance()
    assert done