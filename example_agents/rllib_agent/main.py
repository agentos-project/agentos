import ray
import ray.rllib.agents.registry as rllib_registry
from ray.rllib.agents.trainer import COMMON_CONFIG
from ray.rllib.utils import merge_dicts
from ray.tune.registry import register_env as rllib_reg_env


class RLlibAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(self, algo_name="PPO", trainer_config=None):
        """Init a Ray agent with the given env_class and an algorithm name.

        :param algo_name: A string. For valid values of algo_name, see
        https://github.com/ray-project/ray/blob/master/rllib/agents/registry.py
        """
        if not trainer_config:
            trainer_config = merge_dicts(COMMON_CONFIG, {"framework": "torch"})
        if not ray.is_initialized():
            ray.init()
        env_class = self.env.unwrapped.__class__
        trainer_class = rllib_registry.get_trainer_class(algo_name)

        def wrapper(conf):
            return env_class()  # Ray requires env.__init__() take config.

        rllib_reg_env(env_class.__name__, wrapper)
        self.ray_trainer = trainer_class(
            config=trainer_config, env=env_class.__name__
        )

    def evaluate(self):
        eval_env = self.env.__class__()
        last_obs = eval_env.reset()
        done = False
        while not done:
            action = self.ray_trainer.compute_action(last_obs)
            print(f"decided on action {action}")
            last_obs, _, done, _ = eval_env.step(action)
            print(f"took step, got observation {last_obs}, done = {done}")

    def learn(self, num_iterations: int):
        """Causes Ray to learn"""
        for _ in range(int(num_iterations)):
            self.ray_trainer.train()


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
