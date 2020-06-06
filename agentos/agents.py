"""Implementation of agents available in AgentOS. See core.py for Agent API."""
from agentos import Agent


class RandomAgent(Agent):
    def step(self):
        obs, reward, done, _ = self.env.step(self.env.action_space.sample())
        return done

