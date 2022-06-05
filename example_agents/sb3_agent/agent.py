from gym.wrappers import TimeLimit
from stable_baselines3.common.evaluation import evaluate_policy

from pcs.output import active_output


# A basic agent.
class SB3PPOAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(
        self,
        AtariEnv,
        CartPoleEnv,
        PPO,
        SB3AgentRun,
        env_name: str = "CartPole-v1",
        load_most_recent_run: bool = True,
        model_input_run_id: str = None,
    ):
        self.AtariEnv = AtariEnv
        self.CartPoleEnv = CartPoleEnv
        self.PPO = PPO
        self.SB3AgentRun = SB3AgentRun
        self.env_name = env_name
        self.model_name = f"{self.env_name}-ppo.zip"
        self.environment = self._get_environment()
        assert not (load_most_recent_run and model_input_run_id), (
            "If 'model_input_run_id' is specified, then "
            "'load_most_recent_run' must be False."
        )
        if load_most_recent_run:
            print("Loading most recent model from AgentOS/MLflow.")
            self.model_input_run = (
                self.SB3AgentRun.get_last_learning_run(self.model_name)
            )
            if self.model_input_run:
                policy_path = self.model_input_run.download_artifacts(
                    self.model_name
                )
                self.sb3_ppo = self.PPO.load(policy_path)
                self.sb3_ppo.set_env(self.environment)
                return
        if model_input_run_id:
            print(
                "Loading model from AgentOS/MLflow run "
                f"{model_input_run_id}."
            )
            self.model_input_run = (
                self.SB3AgentRun.from_existing_mlflow_run(
                    model_input_run_id
                )
            )
            policy_path = self.model_input_run.download_artifacts(
                self.model_name
            )
            self.sb3_ppo = self.PPO.load(policy_path)
            self.sb3_ppo.set_env(self.environment)
            return
        self.model_input_run = None
        self.sb3_ppo = self.PPO("MlpPolicy", self.environment)

    def _get_environment(self):
        env_cls = self._get_environment_cls()
        if self.env_name == "PongNoFrameskip-v4":
            env = env_cls(
                game="pong",
                mode=None,
                difficulty=None,
                obs_type="image",
                frameskip=1,
                repeat_action_probability=0.0,
                full_action_space=False,
            )
        elif self.env_name == "CartPole-v1":
            env = env_cls()
        else:
            raise Exception(f"Unknown env_name: {self.env_name}")
        env = TimeLimit(env, 400000)
        return env

    def _get_environment_cls(self):
        if self.env_name == "PongNoFrameskip-v4":
            return self.AtariEnv
        elif self.env_name == "CartPole-v1":
            return self.CartPoleEnv
        else:
            raise Exception(f"Unknown env_name: {self.env_name}")

    @property
    def active_output(self):
        return active_output(self)

    def evaluate(
        self,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        reward_threshold=None,
        return_episode_rewards=False,
        warn=True,
    ):
        env_cls = self._get_environment_cls()
        with self.SB3AgentRun.evaluate_run(
            outer_run=self.active_output,
            model_input_run=self.model_input_run,
            agent_identifier=self.__component__.identifier,
            environment_identifier=env_cls.__component__.identifier,
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
        env_cls = self._get_environment_cls()
        with self.SB3AgentRun.learn_run(
            outer_run=self.active_output,
            model_input_run=self.model_input_run,
            agent_identifier=self.__component__.identifier,
            environment_identifier=env_cls.__component__.identifier,
        ) as learn_run:
            self.sb3_ppo.learn(
                total_timesteps=int(total_timesteps),
                callback=learn_run.learn_callback,
            )
            learn_run.log_model(self.model_name, self.sb3_ppo)
