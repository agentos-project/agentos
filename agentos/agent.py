from threading import Thread
import time

class AgentThread(Thread):
    def __init__(self, brain_clock_freq=2):
        super().__init__()
        self.envs = {}
        self.behaviors = {}
        self.brain_clock_freq = brain_clock_freq
        self.running = False

    def run(self):
        # Main agent consciousness loop.
        self.running = True
        while self.running:
            for b in self.behaviors.values():
                b.step()
            time.sleep(1 / self.brain_clock_freq)

    def stop(self):
        self.running = False

    def add_env(self, env):
        """Registers environment."""
        if not hasattr(env, "last_obs"):
            env.last_obs = None
        self.envs[id(env)] = env

    def remove_env(self, env_id):
        """Deregisters environment."""
        self.envs.pop(env_id)

    def add_behavior(self, behavior, env_id):
        """Adds behavior with given env, which means it starts running."""
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
    print("Agent started.")

def stop_agent():
    global agent
    agent.stop()
    agent.join()
    print("Agent stopped.")
