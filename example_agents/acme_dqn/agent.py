import acme
from acme.agents.tf import dqn
from acme.utils.loggers import Logger
import numpy as np
import statistics


class DQNLogger(Logger):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.episode_data = []

    def write(self, data):
        self.episode_data.append(data)

    # FIXME - Mostly copied+pasted from agentos/core.py
    def print_results(self):
        if not self.episode_data:
            return
        episode_lengths = [d["episode_length"] for d in self.episode_data]
        mean = statistics.mean(episode_lengths)
        median = statistics.median(episode_lengths)
        print()
        print(f"Benchmark results after {len(episode_lengths)} rollouts:")
        print(
            f"\tMax steps over {len(episode_lengths)} trials: "
            f"{max(episode_lengths)}"
        )
        print(f"\tMean steps over {len(episode_lengths)} trials: {mean}")
        print(f"\tMedian steps over {len(episode_lengths)} trials: {median}")
        print(
            f"\tMin steps over {len(episode_lengths)} trials: "
            f"{min(episode_lengths)}"
        )
        print()

    def close(self):
        pass


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
        num_episodes = int(num_episodes)
        print(f"Evaluating agent for {num_episodes} episodes...")
        logger = DQNLogger()
        loop = acme.EnvironmentLoop(
            self.environment,
            self.agent,
            should_update=False,
            logger=logger,
        )
        loop.run(num_episodes=num_episodes)
        logger.print_results()

    def learn(self, num_episodes):
        num_episodes = int(num_episodes)
        print(f"Training agent for {num_episodes} episodes...")
        logger = DQNLogger()
        loop = acme.EnvironmentLoop(
            self.environment,
            self.agent,
            should_update=True,
            logger=logger,
        )
        loop.run(num_episodes=num_episodes)
        logger.print_results()
        self.network.save_tensorflow()
