import tempfile
import shutil
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.policies import BasePolicy
from stable_baselines3.common.callbacks import BaseCallback
from agentos.agent_run import AgentRun
from typing import Optional


class EvaluateCallback:
    """
    Used to log the data from a single evaluation run, which contains a set of
    episodes. For each episode in the set, log the number of steps (into the
    "current_lengths" sequence) and the reward (into the "current_rewards"
    sequence).
    """

    def __init__(self, agent_run: AgentRun):
        self.agent_run = agent_run

    def __call__(self, *args, **kwargs):
        local_vars = args[0]
        current_lengths = local_vars["current_lengths"]
        current_rewards = local_vars["current_rewards"]
        assert len(current_lengths) == 1, "Error: multiple environments"
        assert len(current_rewards) == 1, "Error: multiple environments"
        if local_vars["done"]:
            self.agent_run.add_episode_data(
                steps=current_lengths[0], reward=current_rewards[0]
            )


class LearnCallback(BaseCallback):
    """
    Overrides functionality in ``stable_baselines3.common.callbacks`` that
    SB3's ``evaluate_policy()`` helper method uses to log stats, which is
    used by an agent that depends on this run.

    This callback logs the data from a single learning run, which contains a
    set of episodes. For each episode in the set, log the number of steps (into
    the "current_lengths" sequence) and the reward (into the "current_rewards"
    sequence).
    """

    def __init__(self, run: AgentRun):
        super().__init__()
        self.agent_run = run
        self.curr_steps = 0
        self.curr_reward = 0
        self.last_done = False

    def _on_step(self):
        dones = self.locals["dones"]
        assert len(dones) == 1, "Error: multiple environments"
        self.last_done = dones[0]
        self.curr_steps += 1
        self.curr_reward += self.locals["rewards"][0]
        self.curr_steps
        if self.last_done:
            self._record_episode_data()
        return True

    def on_rollout_end(self):
        # We terminated in the middle of an episode
        if not self.last_done:
            self._record_episode_data()

    def _record_episode_data(self):
        self.agent_run.add_episode_data(
            steps=self.curr_steps, reward=self.curr_reward
        )
        self.curr_steps = 0
        self.curr_reward = 0


class SB3Run(AgentRun):
    """
    An SB3Run must be of type "learn" or "evaluate". Learning runs can have
    log_model() called on them.
    """

    SB3_RUN_TAG_KEY = "sb3_agent_run"

    def __init__(
        self,
        run_type: str,
        parent_run: str = None,
        agent_name: Optional[str] = None,
        environment_name: Optional[str] = None,
    ) -> None:
        super().__init__(
            run_type,
            parent_run=parent_run,
            agent_name=agent_name,
            environment_name=environment_name
        )
        self.evaluate_callback = EvaluateCallback(self)
        self.learn_callback = LearnCallback(self)
        self.set_tag(self.SB3_RUN_TAG_KEY, "True")

    def log_model(self, name: str, policy: BasePolicy):
        assert (
            self.run_type == "learn"
        ), "log_model can only be called by SB3Runs of type 'learn'"
        dir_path = Path(tempfile.mkdtemp())
        policy.save(dir_path / name)
        artifact_path = dir_path / name
        assert artifact_path.is_file()
        self.log_artifact(artifact_path)
        shutil.rmtree(dir_path)

    @classmethod
    def get_last_logged_model(cls, name: str) -> Optional[BasePolicy]:
        """
        Returns the most recent model that was logged by an SB3Run as an
        artifact with filename ``name``.
        :param name: the filename of the artifact to restore.
        :return: Most recently logged model, if one can be found, else None.
        """
        runs = cls._mlflow_client.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.SB3_RUN_TAG_KEY} ILIKE "%"',
        )
        if runs:
            # Since runs is sorted by start_time descending, scan the list
            # for the first run that contains a policy by the name provided.
            for run in runs:
                try:
                    policy_path = cls._mlflow_client.download_artifacts(
                        run.info.run_id, name
                    )
                except IOError:
                    continue  # No policy was logged in this run, keep trying.
                print(f"SB3Run: Found last_logged SB3 policy '{name}'.")
                return PPO.load(policy_path)
        print(f"SB3Run: No SB3 policy with name '{name}' found.")
