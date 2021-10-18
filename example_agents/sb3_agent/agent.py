from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy


# A basic agent.
class SB3PPOAgent:
    def __init__(self):
        super().__init__()
        self.sb3_ppo = self.tracker.restore("ppo")
        if self.sb3_ppo is None:
            self.sb3_ppo = PPO("MlpPolicy", self.environment)
        else:
            self.sb3_ppo.set_env(self.environment)

    def evaluate(
        self,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        callback=None,
        reward_threshold=None,
        return_episode_rewards=False,
        warn=True,
    ):
        with self.tracker.evaluate_run():
            evaluate_policy(
                model=self.sb3_ppo,
                env=self.sb3_ppo.get_env(),
                n_eval_episodes=int(n_eval_episodes),
                deterministic=deterministic,
                render=render,
                callback=self.tracker.evaluate_callback,
                reward_threshold=reward_threshold,
                return_episode_rewards=return_episode_rewards,
                warn=warn,
            )

    def learn(self, total_timesteps=250):
        with self.tracker.learn_run():
            self.sb3_ppo.learn(
                total_timesteps=int(total_timesteps),
                callback=self.tracker.learn_callback,
            )
            self.tracker.save("ppo", self.sb3_ppo)

    def reset(self):
        self.tracker.reset()
