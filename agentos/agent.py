from multiprocessing import Process
import time

class Agent:
    def __init__(self, brain_clock_freq=2):
        super().__init__()
        self.process = None
        self.envs = {}
        self.behaviors = {}
        self.brain_clock_freq = brain_clock_freq
        self.running = False

    def start(self):
        def think():
            # Main agent consciousness loop.
            while self.running:
                for b in self.behaviors.values():
                    b.step()
                time.sleep(1 / self.brain_clock_freq)

        self.running = True
        self.process = Process(target=think)
        self.process.start()
        print("Agent started.")

    def stop(self):
        self.running = False
        print("Agent stopped.")

    def add_env(self, env):
        """Adds environment to agent."""
        if not hasattr(env, "last_obs"):
            env.last_obs = None
        self.envs[id(env)] = env
        return id(env)

    def remove_env(self, env_id):
        """Removes environment from agent."""
        self.envs.pop(env_id)

    def add_behavior(self, behavior, env_id):
        """Adds behavior with given env, which means it starts running."""
        assert env_id in self.envs.keys(), "Specified env not registered."
        behavior.set_env(self.envs[env_id])
        self.behaviors[id(behavior)] = behavior
        return id(behavior)

    def remove_behavior(self, behavior_id):
        """ Deregisters behavior."""
        self.envs.pop(behavior_id)

