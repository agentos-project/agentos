import acme
import numpy as np
from acme.agents.tf import dqn

from pcs import active_component_run


class AcmeDQNAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

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
        with self.AcmeRun.evaluate_run(
            parent_run=active_component_run(self),
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.environment.__component__.identifier,
        ) as run:
            num_episodes = int(num_episodes)
            loop = acme.EnvironmentLoop(
                self.environment,
                self.agent,
                should_update=False,
                logger=run,
            )
            loop.run(num_episodes=num_episodes)

    def learn(self, num_episodes):
        with self.AcmeRun.learn_run(
            parent_run=active_component_run(self),
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.environment.__component__.identifier,
        ) as run:
            num_episodes = int(num_episodes)
            loop = acme.EnvironmentLoop(
                self.environment, self.agent, should_update=True, logger=run
            )
            loop.run(num_episodes=num_episodes)
            self.network.save(run)
