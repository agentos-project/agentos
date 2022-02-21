{file_header}


class BasicDataset:
    def __init__(self):
        self.episodes = []

    def add(self, episode_transitions):
        self.episodes.append(episode_transitions)
