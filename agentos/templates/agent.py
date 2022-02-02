{file_header}


class {agent_name}:
    DEFAULT_ENTRY_POINT = "evaluate"

    def evaluate(self, num_episodes=10):
        for i in range(int(num_episodes)):
            transitions = self.run_episode()
            self.run_manager.record_episode(transitions)
        self.run_manager.print_results()

    def learn(self, num_episodes=10):
        for i in range(int(num_episodes)):
            transitions = self.run_episode()
            self.run_manager.record_episode(transitions)
            for transition in transitions:
                self.dataset.add(*transition)
        self.trainer.train()
        self.run_manager.print_results()

    def run_episode(self):
        curr_obs = self.environment.reset()
        done = False
        transitions = []
        while not done:
            action = self.policy.decide(curr_obs)
            new_obs, reward, done, info = self.environment.step(action)
            transitions.append((curr_obs, action, new_obs, reward, done))
            curr_obs = new_obs
        return transitions
