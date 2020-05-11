import asyncio


class Behavior:
    def __init__(self, config={}):
        self.config = config
        self.env = None
        self.task = None

    def start(self):
        """Starts behavior execution: env step -> behavior step -> loop."""
        raise NotImplementedError

    def stop(self):
        """A blocking call that returns when behavior is stopped."""
        raise NotImplementedError

    def step(self):
        """Decide on next action given and take it in the paired environment."""
        assert self.env, "To step a Behavior, you must pair it with an env."
        assert self.env.last_obs, "To step a Behavior, its env must be reset by AgentOS at least once."
        action = self.get_action(self.last_obs)
        self.env.last_obs, reward, done, _ = self.env.step(action)

    def set_env(self, env):
        self.env = env

    def get_action(self, obs):
        raise NotImplementedError


class AsyncioBehavior(Behavior):
    """A Behavior can only be paired with one environment at a time."""
    def __init__(self, config={}):
        super().__init__(config)

    def start(self):
        async def run_behavior(behavior, hz):
            while True:
                behavior.step()
                asyncio.sleep(1 / hz)

        # TODO: come up w/ a better way to handle default conf vals.
        brain_clock_hz = self.config.get("hz", 2)
        self.task = asyncio.create_task(run_behavior(self, brain_clock_hz))

    def stop(self):
        self.task.cancel()

    def get_action(self, obs):
        raise NotImplementedError
