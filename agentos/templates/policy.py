{file_header}
import agentos
import random


# A random policy
class RandomPolicy(agentos.Policy):
    def decide(self, observation):
        action_space = self.environment.get_spec().actions
        return random.randint(action_space.minimum, action_space.maximum)
