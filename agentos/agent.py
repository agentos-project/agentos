from secrets import token_bytes
from threading import Thread
import time

class AgentThread(Thread):
    def __init__(self, brain_clock_freq=2):
        super().__init__()
        self.envs = {}
        self.behaviors = {}
        self.brain_clock_freq = brain_clock_freq

    def run(self):
        # Main agent consciousness loop.
        while True:
            for b in self.behaviors.values():
                b.step()
            time.sleep(1/self.brain_clock_freq)

    def stop(self):
        self.terminate()

    def add_env(self, env):
        """ Registers environment."""
        if not hasattr(env, "last_obs"):
            env.last_obs = None
        self.envs[id(env)] = env

    def remove_env(self, env_id):
        """ Deregisters environment."""
        self.envs.pop(env_id)

    def add_behavior(self, behavior, env_id):
        """ Registers behavior and starts it with given env."""
        assert env_id in self.envs.keys(), "Specified env not registered."
        behavior.set_env(self, self.envs[env_id])
        self.behaviors[id(behavior)] = behavior

    def remove_behavior(self, behavior_id):
        """ Deregisters behavior."""
        self.envs.pop(behavior_id)


agent = None

def start_agent():
    global agent
    agent = AgentThread()
    agent.start()

def stop_agent():
    global agent
    agent.stop()
