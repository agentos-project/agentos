from agentos import Agent


class RandomAgent(Agent):
    def get_action(self, obs):
        return self.env.action_space.sample()