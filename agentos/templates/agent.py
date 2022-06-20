{file_header}
from pcs.output import active_output


class BasicAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(self, environment_cls, policy, dataset, run_cls):
        self.env_cls = environment_cls
        self.policy = policy
        self.dataset = dataset
        self.run_cls = run_cls

    def evaluate(self, num_episodes=1):
        with self.run_cls.evaluate_run(
            outer_run=active_output(self),
            model_input_run=None,
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.env_cls.__component__.identifier,
        ) as eval_run:
            for i in range(int(num_episodes)):
                self.run_episode()
                eval_run.add_episode_data(
                    steps=self.dataset.last_episode_step_count,
                    reward=self.dataset.last_episode_total_reward,
                )

    def run_episode(self):
        environment = self.env_cls()
        curr_obs = environment.reset()
        done = False
        transitions = []
        while not done:
            action = self.policy.decide(curr_obs)
            new_obs, reward, done, info = environment.step(action)
            transitions.append((curr_obs, action, new_obs, reward, done))
            curr_obs = new_obs
        self.dataset.add(transitions)
        return transitions
