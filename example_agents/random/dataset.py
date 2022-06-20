class BasicDataset:
    def __init__(self):
        self.episodes = []

    def add(self, episode_transitions):
        self.episodes.append(episode_transitions)

    @property
    def last_episode_total_reward(self):
        assert len(self.episodes) > 0
        return sum(t[3] for t in self.episodes[-1])

    @property
    def last_episode_step_count(self):
        assert len(self.episodes) > 0
        return len(self.episodes[-1])
