import time
from threading import Thread, Condition, get_ident

DEFAULT_AGENT_CONFIG = {"stop_when_done": False, "hz": 2}


class AgentManager:
    def __init__(self):
        self.envs = {}
        self.behaviors = {}
        self.running = False

    def start(self):
        if self.running:
            print("AgentManager already running. Nothing to do.")
            return
        self.running = True
        for b in self.behaviors.values():
            b.start()
        print("AgentManager started.")

    def stop(self):
        print("Stopping agent, this may take a long time, depending on the behaviors running.")
        for b in self.behaviors.values():
            b.stop()
        self.running = False
        print("AgentManager stopped.")

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

    def add_agent(self, behavior, env_id):
        """Adds behavior with given env, which means it starts running."""
        assert env_id in self.envs.keys(), "Specified env not registered."
        behavior.set_env(self.envs[env_id])
        self.behaviors[id(behavior)] = behavior
        print(f"Added behavior {id(behavior)}.")
        if self.running:
            print(f"Started behavior {id(behavior)}.")
            behavior.start()
        return id(behavior)

    def remove_agent(self, behavior_id):
        """ Removes & returns behavior."""
        behavior = self.envs.pop(behavior_id)
        print(f"Removed behavior {behavior_id}.")
        return behavior


class Agent:
    """A Agent can only be paired with one environment at a time."""
    def __init__(self, config=DEFAULT_AGENT_CONFIG):
        self.config = config
        self.env = None
        self.last_done = None
        self.last_obs = None
        self.last_reward = None
        self._shutting_down = False  # Breaks run_behavior out of while loop.
        self._thread = None
        self._shutdown_cv = Condition()

    @property
    def running(self):
        return self._thread.is_alive()

    def _run_target(self):
        print(f"_thread {get_ident()} in run_behavior")
        while not self._shutting_down:
            self.step()
            time.sleep(1 / self.config["hz"])
        # Let any threads blocking on stop() know this _thread has in fact finished.
        with self._shutdown_cv:
            self._shutdown_cv.notify_all()

    def start(self):
        if self.last_done:
            print("Cannot start a behavior whose env is done.")
            return
        self._thread = Thread(target=self._run_target)
        self._thread.start()

    def stop(self):
        """Blocking call: returns after self._thread is shutdown."""
        if not self.running:
            print("Nothing for stop() to do, behavior "
                  f"{id(self)}'s _thread not running.")
            return
        self._shutting_down = True
        with self._shutdown_cv:
            self._shutdown_cv.wait()  # Wait till self._thread is out of its loop.
        while self._thread.is_alive():
            time.sleep(.01)
        self._shutting_down = False
        print(f"Agent {id(self)} stopped.")

    def step(self):
        """Decide on next action and take it in the environment."""
        assert self.env, "To step a Agent, you must pair it with an env."
        assert self.last_obs is not None, "Agent.step() requires a last_obs."
        if not self.running:
            print(f"Warning: step() was called on behavior {id(self)} while it "
                  "was not running, which results in a no-op.")
            return
        action = self.get_action(self.last_obs)
        print(f"next action is {action}")
        self.last_obs, self.last_reward, self.last_done, _ = self.env.step(action)
        print(f"Agent {id(self)} took step in env {id(self.env)}")
        if self.last_done and self.config["stop_when_done"]:
            print(f"Agent {id(self)}'s env.step() returned "
                  "done = True, so shutting down thread.")
            self._shutting_down = True

    def set_env(self, env):
        print(env)
        if not self.last_obs:
            try:
                self.last_obs, self.last_reward, self.last_done, _ = env.step(env.action_space.sample())
            except TypeError:
                self.last_obs = env.reset()
        print(f"In behavior, self.last_obs just set to {self.last_obs}")
        self.env = env

    def get_action(self, obs):
        raise NotImplementedError
