import core
from agentos.core import Behavior, DEFAULT_BEHAVIOR_CONFIG
import ray
import ray.rllib.agents.ppo as ppo  # for ppo.DEFAULT_CONFIG
from ray.rllib.agents.ppo import PPOTrainer
from ray.tune.registry import register_env


class RLlibPPOBehavior(Behavior):
    def __init__(self, config=DEFAULT_BEHAVIOR_CONFIG):
        """Init a Ray PPO agent."""
        super().__init__(config)
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
            conf = ppo.DEFAULT_CONFIG.copy()
            conf["env"] = str(id(env))
            self.ray_agent = PPOTrainer(config=conf)

    def get_action(self, obs):
        """Returns next action, given an observation."""
        action = self.ray_agent.compute_action(obs)
        print(f"get_action returning {action}")
        return action

    def train(self, num_iterations):
        """Causes Ray to simulate """
        if self.env:
            self.ray_agent.train(num_iterations)


def test_rllib_ppo_behavior():
    from agentos import AgentManager, DEFAULT_BEHAVIOR_CONFIG
    from gym.envs.classic_control import CartPoleEnv
    import time
    a = AgentManager()
    e_id = a.add_env(CartPoleEnv())
    conf = DEFAULT_BEHAVIOR_CONFIG
    conf["stop_when_done"] = True
    b = RLlibPPOBehavior(config=conf)
    a.add_behavior(b, e_id)
    a.start()
    assert a.running
    time.sleep(1)
    a.stop()
    assert not a.running


if __name__ == "__main__":
    test_rllib_ppo_behavior()