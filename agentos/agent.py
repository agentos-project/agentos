class Agent:
    def __init__(self):
        self.envs = {}
        self.behaviors = {}
        self.running = False

    def start(self):
        # TODO: use MLflow inside this function to record meta-data about
        #       agent instances (including pid, stderr/out, etc.)
        for b in self.behaviors:
            b.start()
        self.running = True
        print("Agent started.")

    def stop(self):
        for b in self.behaviors:
            b.stop()
        self.running = False
        print("Agent stopped.")

    def add_env(self, env):
        """Adds environment to agent."""
        if not hasattr(env, "last_obs"):
            env.last_obs = None
        self.envs[id(env)] = env
        print(f"Added env {id(env)}.")
        return id(env)

    def remove_env(self, env_id):
        """Removes environment from agent."""
        self.envs.pop(env_id)
        print(f"Removed env {env_id}.")

    def add_behavior(self, behavior, env_id, brain_clock_hz=None):
        """Adds behavior with given env, which means it starts running."""
        assert env_id in self.envs.keys(), "Specified env not registered."
        print("Adding behavior.")
        behavior.set_env(self.envs[env_id])
        self.behaviors[id(behavior)] = behavior
        if self.running:
            behavior.start()
        print(f"Added behavior {id(behavior)}.")
        return id(behavior)

    def remove_behavior(self, behavior_id):
        """ Deregisters behavior."""
        self.envs.pop(behavior_id)
        print(f"Removed behavior {behavior_id}.")
