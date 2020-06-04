"""Core AgentOS APIs."""
import time
from threading import Thread


class Agent:
    def __init__(self, env_class):
        """Set self.env, then reset the env and store _last_obs."""
        self.env = env_class()
        self.init_obs = self.env.reset()

    def step(self):
        raise NotImplementedError


def run_agent(agent_class, env, hz=40, as_thread=False):
    """Run an agent in this thread."""
    def runner():
        agent_instance = agent_class(env)
        done = False
        while not done:
            done = agent_instance.step()
            time.sleep(1 / hz)
    if as_thread:
        Thread(target=runner).start()
    else:
        runner()
