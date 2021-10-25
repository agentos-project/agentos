import acme
from acme.agents.tf import dqn
import numpy as np


class AcmeDQNAgent:
    def __init__(self, **kwargs):
        self.discount = (np.float32(kwargs["discount"]),)
        self.agent = dqn.DQN(
            environment_spec=self.environment.get_spec(),
            network=self.network.net,
            discount=self.discount,
            batch_size=int(kwargs["batch_size"]),
            samples_per_insert=int(kwargs["samples_per_insert"]),
            min_replay_size=int(kwargs["min_replay_size"]),
        )

    def evaluate(self, num_episodes):
        with self.tracker.evaluate_run():
            num_episodes = int(num_episodes)
            loop = acme.EnvironmentLoop(
                self.environment,
                self.agent,
                should_update=False,
                logger=self.tracker,
            )
            loop.run(num_episodes=num_episodes)

    def learn(self, num_episodes):
        with self.tracker.learn_run():
            num_episodes = int(num_episodes)
            loop = acme.EnvironmentLoop(
                self.environment,
                self.agent,
                should_update=True,
                logger=self.tracker,
            )
            loop.run(num_episodes=num_episodes)
            self.network.save()

    def reset(self):
        self.tracker.reset()
