from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from agentos import active_component_run


# A basic agent.
class SB3PPOAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(self):
        super().__init__()
        self.sb3_ppo = self.SB3AgentRun.get_last_logged_model("ppo.zip")
        if self.sb3_ppo is None:
            self.sb3_ppo = PPO("MlpPolicy", self.environment)
        else:
            self.sb3_ppo.set_env(self.environment)

    @property
    def active_run(self):
        return active_component_run(self)

    def evaluate(
        self,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        reward_threshold=None,
        return_episode_rewards=False,
        warn=True,
    ):
        with self.SB3AgentRun(
            run_type="evaluate", parent_run=self.active_run
        ) as eval_run:
            evaluate_policy(
                model=self.sb3_ppo,
                env=self.sb3_ppo.get_env(),
                n_eval_episodes=int(n_eval_episodes),
                deterministic=deterministic,
                render=render,
                callback=eval_run.evaluate_callback,
                reward_threshold=reward_threshold,
                return_episode_rewards=return_episode_rewards,
                warn=warn,
            )

    def learn(self, total_timesteps=250):
        with self.SB3AgentRun("learn", self.active_run) as learn_run:
            self.sb3_ppo.learn(
                total_timesteps=int(total_timesteps),
                callback=learn_run.learn_callback,
            )
            learn_run.log_model("ppo.zip", self.sb3_ppo)
