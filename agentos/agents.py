"""Implementation of agents available in AgentOS. See core.py for Agent API."""
from agentos import Agent


class RandomAgent(Agent):
    """Extremely simple agent that takes random steps in self.env till done."""
    def _init(self):
        self.step_count = 0
        print("Created RandomAgent!")

    def advance(self):
        obs, reward, done, _ = self.env.step(self.env.action_space.sample())
        print(f"Taking random step {self.step_count}.")
        self.step_count += 1
        return done

