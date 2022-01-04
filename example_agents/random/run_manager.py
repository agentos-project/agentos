from statistics import mean, median


class RandomRunManager:
    def __init__(self):
        self.episodes = []

    def record_episode(self, transitions):
        self.episodes.append(transitions)

    def print_results(self):
        episode_lengths = [len(e) for e in self.episodes]
        print(
            f"\nResults after {len(self.episodes)} episodes\n"
            f"\tMax episode transitions: {max(episode_lengths)}\n"
            f"\tMedian episode transitions: {median(episode_lengths)}\n"
            f"\tMean episode transitions: {mean(episode_lengths)}\n"
            f"\tMin episode transitions: {min(episode_lengths)}\n"
        )
