# This file was auto-generated by `agentos init` on Sep 14, 2021 15:53:51.
import agentos


class PPOPolicy(agentos.Policy):
    def decide(self, observation, actions):
        return self.trainer.sb3_ppo.predict(observation)[0]