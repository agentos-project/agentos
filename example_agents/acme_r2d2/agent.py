import acme

from pcs import active_output


class AcmeR2D2Agent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(
        self, environment, policy, dataset, trainer, AcmeRun, network, **kwargs
    ):
        self.environment = environment
        self.policy = policy
        self.dataset = dataset
        self.trainer = trainer
        self.AcmeRun = AcmeRun
        self.network = network

    def evaluate(self, num_episodes):
        with self.AcmeRun.evaluate_run(
            outer_run=active_output(self),
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.environment.__component__.identifier,
        ) as run:
            loop = acme.EnvironmentLoop(
                self.environment,
                self,
                should_update=False,
                logger=run,
            )
            loop.run(num_episodes=int(num_episodes))

    def learn(self, num_episodes):
        with self.AcmeRun.learn_run(
            outer_run=active_output(self),
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.environment.__component__.identifier,
        ) as run:
            loop = acme.EnvironmentLoop(
                self.environment,
                self,
                should_update=True,
                logger=run,
            )
            loop.run(num_episodes=int(num_episodes))
            self.network.save(run=run)

    # Acme agent API
    def observe_first(self, timestep):
        self.dataset.add_first(timestep)

    # Acme agent API
    def select_action(self, observation):
        return self.policy.decide(observation)

    # Acme agent API
    def observe(self, action, next_timestep):
        self.dataset.add(action, next_timestep)

    # Acme agent API
    def update(self):
        self.trainer.improve()


def run_tests():
    pass


if __name__ == "__main__":
    run_tests()
