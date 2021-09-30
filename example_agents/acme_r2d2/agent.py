import agentos


class R2D2Agent(agentos.Agent):
    def evaluate(
        self,
        num_episodes,
        should_learn=False,
        max_transitions=None,
        backup_dst=None,
        print_stats=True,
    ):
        """Runs an agent specified by a given [agent_file]

        :param num_episodes: number of episodes to run the agent through
        :param should_learn: boolean, if True we will call policy.improve
        :param max_transitions: If not None, max transitions performed before
                                truncating an episode.
        :param backup_dst: if specified, will print backup path to stdout
        :param print_stats: if True, will print run stats to stdout

        :returns: None
        """
        print("running Acme R2D2 agent")
        all_steps = []
        for i in range(int(num_episodes)):
            steps = self.rollout(
                should_learn=should_learn, max_transitions=max_transitions
            )
            all_steps.append(steps)
        print(f"print_stats is {print_stats}")
        if (
            print_stats != "False"
            and print_stats != "false"
            and print_stats != "f"
        ):
            self._print_run_results(all_steps, backup_dst)

    def learn(
        self,
        num_episodes,
        test_every,
        test_num_episodes,
        max_transitions=None,
    ):
        """Trains an agent by calling its learn() method in a loop."""
        num_episodes = int(num_episodes)
        test_num_episodes = int(test_num_episodes)
        # Handle strings from -P
        # TODO: fix that ugliness!
        if isinstance(test_every, str):
            test_every = False
            if test_every == "True":
                test_every = True
        test_every = int(test_every)
        run_size = test_every if test_every else num_episodes
        total_episodes = 0

        while total_episodes < num_episodes:
            if test_every:
                backup_dst = self._backup_agent(self.backing_dir)
                self.evaluate(
                    num_episodes=test_num_episodes,
                    should_learn=False,
                    max_transitions=max_transitions,
                    backup_dst=backup_dst,
                    print_stats=True,
                )
            self.evaluate(
                num_episodes=run_size,
                should_learn=True,
                max_transitions=max_transitions,
                backup_dst=None,
                print_stats=True,
            )
            total_episodes += run_size


def run_tests():
    pass


if __name__ == "__main__":
    run_tests()
