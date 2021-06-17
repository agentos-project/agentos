{file_header}
import agentos
import random


# A random policy
class RandomPolicy(agentos.Policy):
    def decide(self, observation, actions):
        return random.choice(actions)

    def improve(self, **kwargs):
        pass

    def observe(self, action, observation, reward, done, info):
        pass
