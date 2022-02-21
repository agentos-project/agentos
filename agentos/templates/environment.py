{file_header}


# Simulates a 1D corridor
class Corridor:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.length = 5
        self.action_space = [0, 1]
        self.observation_space = [0, 1, 2, 3, 4, 5]
        self.reset()

    def step(self, action):
        assert action in self.action_space
        if action == 0:
            self.position = max(self.position - 1, 0)
        else:
            self.position = min(self.position + 1, self.length)
        return (self.position, -1, self.done, dict())

    def reset(self):
        self.position = 0
        return self.position

    @property
    def valid_actions(self):
        return self.action_space

    @property
    def done(self):
        return self.position >= self.length
