import agentos


class R2D2Agent(agentos.Agent):
    entry_points = ["run"]
    pass

    def run(self,
            agentos_dir,
            num_episodes,
            should_learn=False,
            max_transitions=None,
            backup_dst=None,
            print_stats=False,
            verbose=False,
            ):
        """Runs an agent specified by a given [agent_file]

        :param num_episodes: number of episodes to run the agent through
        :param should_learn: boolean, if True we will call policy.improve
        :param max_transitions: If not None, max transitions performed before
                                truncating an episode.
        :param backup_dst: if specified, will print backup path to stdout
        :param print_stats: if True, will print run stats to stdout
        :param verbose: boolean, if True will print debugging data to stdout

        :returns: None
        """
        all_steps = []
        for i in range(int(num_episodes)):
            steps = self.rollout(
                should_learn=should_learn, max_transitions=max_transitions
            )
            all_steps.append(steps)


def run_tests():
    pass


if __name__ == "__main__":
    run_tests()
