"""Core AgentOS APIs."""
import time
from threading import Thread, Condition, get_ident

DEFAULT_AGENT_CONFIG = {"stop_when_done": False, "hz": 2}


def generate_id(obj):
    return id(obj)  # Keep it simple for now.


class AgentManager:
    def __init__(self):
        self.envs = {}
        self.agents = {}

    def add_env(self, env, env_id=None):
        """Adds environment."""
        e_id = env_id or id(env)
        self.envs[e_id] = env
        print(f"Added env {e_id}.")
        return e_id

    def remove_env(self, env_id):
        """Removes & returns environment."""
        env = self.envs.pop(env_id)
        print(f"Removed env {env_id}.")
        return env

    def add_agent(self, agent, env_id=None, agent_id=None, auto_start=False):
        """
        Adds Agent, optionally assigns an env to it. If it has an env already,
        then check that its env has been added to this AgentManager, and if
        it has not then add it.
        """
        a_id = agent_id or generate_id(agent)
        self.agents[a_id] = agent
        print(f"Added agent {a_id}.")
        if agent.env:
            assert env_id is None, f"Agent {a_id} already has an env."
            # make sure env is already added to this AgentManager,
            # if it isn't then add it.
            if agent.env not in self.envs.items():
                self.envs[generate_id(agent.env)] = agent.env
        if env_id:
            assert env_id in self.envs.keys(), "Specified env not found."
            agent.set_env(self.envs[env_id])
        if auto_start:
            assert agent.env, f"Agent {a_id} has no env, cannot auto_start."
            agent.start()
            print(f"Started agent {a_id}.")
        return a_id

    def remove_agent(self, agent_id):
        """ Removes & returns agent."""
        agent = self.envs.pop(agent_id)
        print(f"Removed agent {agent_id}.")
        return agent

    def assign_env(self, agent_id, env_id):
        assert env_id in self.envs.keys(), "Specified env not found."
        assert agent_id in self.agents.keys(), "Specified agent not found."
        agent = self.agents[agent_id]
        assert agent.env is None, f"Agent {agent_id} already has an env."
        agent.set_env(self.envs[env_id])


class Agent:
    """A Agent can only be paired with one environment at a time."""
    def __init__(self, config=DEFAULT_AGENT_CONFIG):
        self.config = config
        self.env = None
        self.last_done = None
        self.last_obs = None
        self.last_reward = None
        self._shutting_down = False  # Breaks run_agent out of while loop.
        self._thread = None
        self._shutdown_cv = Condition()

    @property
    def running(self):
        return self._thread.is_alive()

    def _run_target(self):
        print(f"_thread {get_ident()} in run_agent")
        while not self._shutting_down:
            self.step()
            time.sleep(1 / self.config["hz"])
        # Let any threads blocking on stop() know this _thread has in fact finished.
        with self._shutdown_cv:
            self._shutdown_cv.notify_all()

    def start(self):
        if self.last_done:
            print("Cannot start a agent whose env is done.")
            return
        self._thread = Thread(target=self._run_target)
        self._thread.start()

    def stop(self):
        """Blocking call: returns after self._thread is shutdown."""
        if not self.running:
            print("Nothing for stop() to do, agent "
                  f"{self}'s _thread not running.")
            return
        self._shutting_down = True
        with self._shutdown_cv:
            self._shutdown_cv.wait()  # Wait till self._thread is out of its loop.
        while self._thread.is_alive():
            time.sleep(.01)
        self._shutting_down = False
        print(f"Agent {self} stopped.")

    def step(self):
        """Decide on next action and take it in the environment."""
        assert self.env, "To step a Agent, you must pair it with an env."
        assert self.last_obs is not None, "Agent.step() requires a last_obs."
        if not self.running:
            print(f"Warning: step() was called on agent {self} while it "
                  "was not running, which results in a no-op.")
            return
        action = self.get_action(self.last_obs)
        print(f"next action is {action}")
        self.last_obs, self.last_reward, self.last_done, _ = self.env.step(action)
        print(f"Agent {self} took step in env {self.env}")
        if self.last_done and self.config["stop_when_done"]:
            print(f"Agent {self}'s env.step() returned "
                  "done = True, so shutting down thread.")
            self._shutting_down = True

    def set_env(self, env):
        print(env)
        if not self.last_obs:
            try:
                self.last_obs, self.last_reward, self.last_done, _ = env.step(env.action_space.sample())
            except TypeError:
                self.last_obs = env.reset()
        print(f"In agent, self.last_obs just set to {self.last_obs}")
        self.env = env

    def get_action(self, obs):
        raise NotImplementedError
