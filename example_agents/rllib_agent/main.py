from agentos import Agent
from agentos import DEFAULT_AGENT_CONFIG as AGENTOS_DEFAULT_AGENT_CONFIG
import ray
import ray.rllib.agents.registry


class RLlibPPOAgent(Agent):
    def __init__(self, config=AGENTOS_DEFAULT_AGENT_CONFIG):
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



    def step(self, obs):
        """Returns next action, given an observation."""
        action = self.ray_agent.compute_action(obs)
        print(f"RLlibAgent.step returning {action}")
        return action

    def train(self, num_iterations):
        """Causes Ray to simulate """
        if self.env:
            self.ray_agent.train(num_iterations)


def test_rllib_ppo_agent():
    from agentos import AgentManager, DEFAULT_AGENT_CONFIG
    from gym.envs.classic_control import CartPoleEnv
    import time
    a = AgentManager()
    e_id = a.add_env(CartPoleEnv())
    conf = DEFAULT_AGENT_CONFIG
    conf["stop_when_done"] = True
    b = RLlibPPOAgent(config=conf)
    a.add_agent(b, env_id=e_id, auto_start=True)
    assert b.running
    time.sleep(1)
    b.stop()
    assert not b.running

