from agentos.behavior import Behavior
import ray
from ray.rllib.agents.ppo import PPOTrainer, DEFAULT_CONFIG

class RLlibPPOBehavior(Behavior):
    def __init__(self):
        """Init a Ray PPO agent."""
        super().__init__()
        if not ray.is_initialized():
            ray.init()
        self.config["ray_config"] = DEFAULT_CONFIG.copy()
        self.ray_agent = PPOTrainer(config=self.config["ray_config"])

    # Override parent's implementation.
    def set_env(self, env):
        """Accepts a gym env and updates the ray agent to use that env."""
        super().set_env(env)
        ray_conf = self.ray_agent.config
        ray_conf["env"] = type(env)
        self.ray_agent.reset_config(ray_conf)

    def get_action(self, obs):
        """Returns next action, given an observation."""
        self.ray_agent.compute_action(obs)

    def train(self, num_iterations):
        """Causes Ray to simulate """
        if self.env:
            self.ray_agent.train(num_iterations)
