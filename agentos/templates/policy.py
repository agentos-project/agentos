{file_header}
import random


class RandomPolicy:
    def decide(self, observation):
        return random.choice(self.environment.action_space)
