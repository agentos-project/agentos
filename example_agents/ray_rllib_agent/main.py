from agentos.behavior import AsyncioBehavior
import ray
from ray.rllib.agents.ppo import PPOTrainer, DEFAULT_CONFIG
from ray.tune.logger import pretty_print
from ray.tune.registry import register_env


class RLlibPPOBehavior(AsyncioBehavior):
    def __init__(self):
        """Init a Ray PPO agent."""
        super().__init__()
        if not ray.is_initialized():
            ray.init()
        # RLlib agents require an env to be initialized, so we do it in set_env().
        self.ray_agent = None

    # Override parent implementation.
    def set_env(self, env):
        """Accepts a gym env and updates the ray agent to use that env."""
        super().set_env(env)

        # An RLlib agent can't take a vanilla gym env class since RLlib
        # requires the env class __init__() function to take an env_config arg.
        # RLlib does support passing in function that thinly wraps an env
        # like below. See https://docs.ray.io/en/latest/rllib-env.html
        # TODO: Fix this because this isn't going to work for training!
        def env_creator(conf):
            return env
        register_env(str(id(env)), env_creator)
        if self.ray_agent:
            conf = self.ray_agent.config
            conf["env"] = str(id(env))
            self.ray_agent.reset_config(conf)
        else:
            conf = DEFAULT_CONFIG.copy()
            conf["env"] = str(id(env))
            print(f"conf is now: {pretty_print(conf)}")
            self.ray_agent = PPOTrainer(config=conf)

    def get_action(self, obs):
        """Returns next action, given an observation."""
        self.ray_agent.compute_action(obs)

    def train(self, num_iterations):
        """Causes Ray to simulate """
        if self.env:
            self.ray_agent.train(num_iterations)

def test_RLlibPPOBehavior():
    from agentos.agent import Agent
    from gym.envs.classic_control import CartPoleEnv
    a = Agent()
    e_id = a.add_env(CartPoleEnv())
    b = RLlibPPOBehavior()
    a.add_behavior(b, e_id)
    a.start()
