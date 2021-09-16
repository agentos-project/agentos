import agentos


class R2D2Agent(agentos.Agent):

    def advance(self):
        """Takes one action within the Environment as dictated by the Policy"""
        if self._should_reset:
            self.curr_obs = self.environment.reset()
            self._should_reset = False
            self.dataset.add(None, None, self.curr_obs, None, None, {})
        action = self.policy.decide(
            self.curr_obs, self.environment.valid_actions
        )
        prev_obs = self.curr_obs
        self.curr_obs, reward, done, info = self.environment.step(action)
        self.dataset.add(prev_obs, action, self.curr_obs, reward, done, info)
        if done:
            self._should_reset = True
        return prev_obs, action, self.curr_obs, reward, done, info


def run_tests():
    pass


if __name__ == "__main__":
    run_tests()
