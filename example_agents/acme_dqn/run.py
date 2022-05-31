from agentos.agent_output import AgentOutput


# Adheres to Acme Logger interface
# https://github.com/deepmind/acme/blob/master/acme/utils/loggers/base.py
class AcmeRun(AgentOutput):
    # Acme logger API
    def write(self, data: dict):
        self.add_episode_data(
            steps=data["episode_length"],
            reward=data["episode_return"].item(),
        )

    # Acme logger API
    def close(self):
        pass
