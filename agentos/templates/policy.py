{file_header}
import random


class RandomPolicy:
    def __init__(self, environment):
        self.environment = environment

    def decide(self, observation):
        return random.choice(self.environment.action_space)
