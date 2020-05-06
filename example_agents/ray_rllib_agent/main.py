from agentos.behavior import Behavior
import ray
from ray.rllib.agents.ppo import PPOTrainer, DEFAULT_CONFIG

class RLlibPPOBehavior(Behavior):
    def __init__(self, agent):
        """Init a Ray PPO agent."""
        super().__init__(agent)
        self.config["ray_config"] = DEFAULT_CONFIG.copy()

        if not ray.is_initialized():
            ray.init()
        self.ray_agent = PPOTrainer(self.config)

    def set_env(self, env):
        """Accepts a gym env and updates the ray agent to use that env."""
        self.env = env
        conf = self.ray_agent.config
        conf["env"] = env
        self.ray_agent.reset_config(conf)

    def get_action(self, observation):
        self.ray_agent.compute_action(observation)

    def train(self, num_iterations):
        if self.env:
            self.ray_agent.train(num_iterations)
