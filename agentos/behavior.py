class Behavior:
    """A Behavior can only be paired with one environment at a time."""
    def __init__(self, agent, config={}):
        self.agent = agent
        self.config = config
        self.env = None

    def step(self):
        assert self.env, "To step a Behavior, you must pair it with an env."
        assert self.env.last_obs, "To step a Behavior, its env must be reset by AgentOS at least once."
        action = self.get_action(self.last_obs)
        self.env.last_obs, reward, done, _ = self.env.step(action)

    def set_env(self, env):
        raise NotImplementedError

    def get_action(self, obs):
        raise NotImplementedError
