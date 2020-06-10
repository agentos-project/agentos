"""Core AgentOS APIs."""
import time
from threading import Thread


class Agent:
    def __init__(self, env_class):
        """Set self.env, then reset the env and store _last_obs."""
        self.env = env_class()
        self.init_obs = self.env.reset()

    def step(self):
        """Returns True when agent is done."""
        raise NotImplementedError


def run_agent(agent_class, env, hz=40, as_thread=False, **kwargs):
    """Run an agent, optionally in a new thread.

    If as_thread is True, agent is run in a thread, and the
    thread object is returned to the caller. The caller may
    need to call join on that that thread depending on their
    use case for this agent_run.
    """
    def runner():
        agent_instance = agent_class(env, **kwargs)
        done = False
        while not done:
            done = agent_instance.step()
            time.sleep(1 / hz)
    if as_thread:
        return Thread(target=runner).start()
    else:
        runner()
