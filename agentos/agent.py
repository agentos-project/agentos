class Agent:
    def __init__(self):
        self.envs = {}
        self.behaviors = {}
        self.running = False

    def start(self):
        # TODO: use MLflow inside this function to record meta-data about
        #       agent instances (including pid, stderr/out, etc.)
        self.running = True
        for b in self.behaviors.values():
            b.start()
        print("Agent started.")

    def stop(self):
        print("Stopping agent, this may take a long time, depending on the behaviors running.")
        for b in self.behaviors.values():
            b.stop()
        self.running = False
        print("Agent stopped.")

    def add_env(self, env):
        """Adds environment to agent."""
        self.envs[id(env)] = env
        print(f"Added env {id(env)}.")
        return id(env)

    def remove_env(self, env_id):
        """Removes & returns environment."""
        env = self.envs.pop(env_id)
        print(f"Removed env {env_id}.")
        return env

    def add_behavior(self, behavior, env_id):
        """Adds behavior with given env, which means it starts running."""
        assert env_id in self.envs.keys(), "Specified env not registered."
        behavior.set_env(self.envs[env_id])
        self.behaviors[id(behavior)] = behavior
        print(f"Added behavior {id(behavior)}.")
        if self.running:
            print(f"Started behavior {id(behavior)}.")
            behavior.start()
        return id(behavior)

    def remove_behavior(self, behavior_id):
        """ Removes & returns behavior."""
        behavior = self.envs.pop(behavior_id)
        print(f"Removed behavior {behavior_id}.")
        return behavior

