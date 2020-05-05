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
        # Main brain consciousness loop.
        while True:
            print("agent brain clock firing in AgentThread.run()")
            time.sleep(1/self.brain_clock_freq)

    def stop(self):
        self.terminate()

    def register_behavior(self, behavior):
        """ Registers behavior and returns the behavior_id"""
        behavior_id = token_bytes()
        self.behaviors[behavior_id] = behavior
        behavior.start(self)
        return behavior_id

    def deregister_behavior(self, behavior_id):
        """ Deregisters behavior."""
        self.envs.pop(behavior_id)

    def register_env(self, env):
        """ Registers environment and returns the env_id"""
        env_id = token_bytes()
        self.envs[env_id] = env
        return env_id

    def deregister_env(self, env_id):
        """ Deregisters environment."""
        self.envs.pop(env_id)


agent = None

def start_agent():
    global agent
    agent = AgentThread()
    agent.start()

def stop_agent():
    global agent
    agent.stop()
