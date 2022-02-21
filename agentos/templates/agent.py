{file_header}
from statistics import mean, median


class {agent_name}:
    DEFAULT_ENTRY_POINT = "run_episodes"

    def run_episodes(self, num_episodes=1):
        for i in range(int(num_episodes)):
            self.run_episode()
        self.print_results()

    def run_episode(self):
        curr_obs = self.environment.reset()
        done = False
        transitions = []
        while not done:
            action = self.policy.decide(curr_obs)
            new_obs, reward, done, info = self.environment.step(action)
            transitions.append((curr_obs, action, new_obs, reward, done))
            curr_obs = new_obs
        self.dataset.add(transitions)

    def print_results(self):
        episode_lengths = [len(e) for e in self.dataset.episodes]
        print("\nResults after", len(self.dataset.episodes), "episodes")
        print("\tMax episode transitions:", max(episode_lengths))
        print("\tMedian episode transitions:", median(episode_lengths))
        print("\tMean episode transitions:", mean(episode_lengths))
        print("\tMin episode transitions:", min(episode_lengths))
