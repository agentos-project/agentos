from gym.wrappers import TimeLimit
from stable_baselines3.common.evaluation import evaluate_policy

from pcs.component_run import active_component_run


# A basic agent.
class SB3PPOAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(
        self,
        load_most_recent_run: bool = True,
        model_input_run_id: str = None,
    ):
        self.environment = self._get_environment()
        assert not (load_most_recent_run and model_input_run_id), (
            "If 'model_input_run_id' is specified, then "
            "'load_most_recent_run' must be False."
        )
        if load_most_recent_run:
            print("Loading most recent model from AgentOS/MLflow.")
            self.model_input_run = self.SB3AgentRun.get_last_learning_run(
                "ppo.zip"
            )
            if self.model_input_run:
                policy_path = self.model_input_run.download_artifacts(
                    "ppo.zip"
                )
                self.sb3_ppo = self.PPO.load(policy_path)
                self.sb3_ppo.set_env(self.environment)
                return
        if model_input_run_id:
            print(
                f"Loading model from AgentOS/MLflow run {model_input_run_id}."
            )
            self.model_input_run = self.SB3AgentRun.from_existing_run_id(
                model_input_run_id
            )
            policy_path = self.model_input_run.download_artifacts("ppo.zip")
            self.sb3_ppo = self.PPO.load(policy_path)
            self.sb3_ppo.set_env(self.environment)
            return
        self.model_input_run = None
        self.sb3_ppo = self.PPO("MlpPolicy", self.environment)

    def _get_environment(self):
        env = self.AtariEnv(
            game="pong",
            mode=None,
            difficulty=None,
            obs_type="image",
            frameskip=1,
            repeat_action_probability=0.0,
            full_action_space=False,
        )
        env = TimeLimit(env, 400000)
        return env

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
        with self.SB3AgentRun.evaluate_run(
            outer_run=self.active_run,
            model_input_run=self.model_input_run,
            agent_identifier=self.PPO.__component__.identifier,
            environment_identifier=self.AtariEnv.__component__.identifier,
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
        with self.SB3AgentRun.learn_run(
            outer_run=self.active_run,
            model_input_run=self.model_input_run,
            agent_identifier=self.PPO.__component__.identifier,
            environment_identifier=self.AtariEnv.__component__.identifier,
        ) as learn_run:
            self.sb3_ppo.learn(
                total_timesteps=int(total_timesteps),
                callback=learn_run.learn_callback,
            )
            learn_run.log_model("ppo.zip", self.sb3_ppo)
