{file_header}
import random


class RandomPolicy:
    def __init__(self, environment_cls):
        self.environment_cls = environment_cls

    def decide(self, observation):
        return random.choice(self.environment_cls.action_space)
