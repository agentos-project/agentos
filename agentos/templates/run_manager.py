{file_header}
from statistics import mean, median


class BasicRunManager:
    def __init__(self):
        self.episodes = []

    def record_episode(self, transitions):
        self.episodes.append(transitions)

    def print_results(self):
        episode_lengths = [len(e) for e in self.episodes]
        print("\nResults after", len(self.episodes), "episodes")
        print("\tMax episode transitions:", max(episode_lengths))
        print("\tMedian episode transitions:", median(episode_lengths))
        print("\tMean episode transitions:", mean(episode_lengths))
        print("\tMin episode transitions:", min(episode_lengths))