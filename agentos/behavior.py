from threading import Thread, Condition, get_ident
import time

DEFAULT_CONFIG = {"stop_when_done": False,
                  "hz": 2}

class Behavior:
    """A Behavior can only be paired with one environment at a time."""
    def __init__(self, config=DEFAULT_CONFIG):
        self.config = config
        self.env = None
        self.last_done = None
        self.last_obs = None
        self.last_reward = None
        self.shutting_down = False  # Breaks run_behavior out of while loop.
        self.thread = Thread(target=self._thread_target)
        self._shutdown_cv = Condition()

    @property
    def running(self):
        return self.thread.is_alive()

    def _thread_target(self):
        print(f"thread {get_ident()} in run_behavior")
        while not self.shutting_down:
            self.step()
            time.sleep(1 / self.config["hz"])
        # Let any threads blocking on stop() know this thread has in fact finished.
        with self._shutdown_cv:
            self._shutdown_cv.notify_all()

    def start(self):
        if self.last_done:
            print("Cannot start a behavior whose env is done.")
            return
        self.thread.start()

    def stop(self):
        """Initiates a thread shutdown and returns after self.thread is shutdown."""
        if not self.running:
            print("Nothing for stop() to do, behavior "
                  f"{id(self)}'s thread not running.")
            return
        self.shutting_down = True
        with self._shutdown_cv:
            self._shutdown_cv.wait()  # Wait till self.thread is out of its loop.
        while self.thread.is_alive():
            time.sleep(.1)
        self.shutting_down = False
        print(f"Behavior {id(self)} stopped.")

    def step(self):
        """Decide on next action given and take it in the paired environment."""
        assert self.env, "To step a Behavior, you must pair it with an env."
        assert self.last_obs is not None, "Behavior.step() requires a last_obs."
        if not self.running:
            print(f"Warning: step() was called on behavior {id(self)} while it "
                  "was not running, which results in a no-op.")
            return
        action = self.get_action(self.last_obs)
        print(f"next action is {action}")
        self.last_obs, self.last_reward, self.last_done, _ = self.env.step(action)
        print(f"Behavior {id(self)} took step in env {id(self.env)}")
        if self.last_done and self.config["stop_when_done"]:
            print(f"Behavior {id(self)}'s env.step() returned " 
                  "done = True, shutting down.")
            self.shutting_down = True

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
