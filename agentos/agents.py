"""Implementation of agents available in AgentOS. See core.py for Agent API."""
from agentos import Agent
from agentos import Policy


class RandomPolicy(Policy):
    def improve(self, *args, **kwargs):
        pass

    def decide(self, observation, action_space):
        return action_space.sample()


class RandomAgent(Agent):
    """Extremely simple agent that takes random steps in self.env till done."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = RandomPolicy()
        self.step_count = 0
        print("Created RandomAgent!")

    def learn(self):
        pass

    def advance(self):
        action = self.policy.decide(None, self.environment.action_space)
        obs, reward, done, _ = self.environment.step(action)
        print(f"Taking random step {self.step_count}.")
        self.step_count += 1
        return done
