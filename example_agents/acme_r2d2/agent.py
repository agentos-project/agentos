import acme


class AcmeR2D2Agent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(self, *args, **kwargs):
        pass

    def evaluate(self, num_episodes):
        with self.run_manager.evaluate_run():
            loop = acme.EnvironmentLoop(
                self.environment,
                self,
                should_update=False,
                logger=self.run_manager,
            )
            loop.run(num_episodes=int(num_episodes))

    def learn(self, num_episodes):
        with self.run_manager.learn_run():
            loop = acme.EnvironmentLoop(
                self.environment,
                self,
                should_update=True,
                logger=self.run_manager,
            )
            loop.run(num_episodes=int(num_episodes))
            self.network.save()

    def reset(self):
        self.run_manager.reset()

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
