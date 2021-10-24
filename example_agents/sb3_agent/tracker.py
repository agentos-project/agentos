import mlflow
import tempfile
import shutil
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.policies import BasePolicy
from stable_baselines3.common.callbacks import BaseCallback
from agentos.tracker import AgentTracker
from typing import Optional


class EvaluateCallback:
    def __init__(self, tracker: AgentTracker):
        self.tracker = tracker

    def __call__(self, *args, **kwargs):
        local_vars = args[0]
        current_lengths = local_vars["current_lengths"]
        current_rewards = local_vars["current_rewards"]
        assert len(current_lengths) == 1, "Error: multiple environments"
        assert len(current_rewards) == 1, "Error: multiple environments"
        if local_vars["done"]:
            episodes = 0
            steps = 0
            if len(self.tracker.episode_data) > 0:
                episodes = self.tracker.episode_data[-1]["episodes"]
                steps = self.tracker.episode_data[-1]["steps"]

            self.tracker.episode_data.append(
                {
                    "episode_length": current_lengths[0],
                    "episode_reward": current_rewards[0],
                    "episodes": episodes + 1,
                    "steps": steps + current_lengths[0],
                }
            )


class LearnCallback(BaseCallback):
    def __init__(self, tracker: AgentTracker):
        super().__init__()
        self.tracker = tracker
        self.curr_steps = 0
        self.curr_reward = 0
        self.last_done = False
        self.total_episodes = 0
        self.total_steps = 0

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
        self.total_episodes += 1
        self.total_steps += self.curr_steps
        self.tracker.episode_data.append(
            {
                "episode_length": self.curr_steps,  # this episode
                "episode_reward": self.curr_reward,  # this episode
                "episodes": self.total_episodes,
                "steps": self.total_steps,
            }
        )
        self.curr_steps = 0
        self.curr_reward = 0


class SB3Tracker(AgentTracker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.evaluate_callback = EvaluateCallback(self)
        self.learn_callback = LearnCallback(self)

    def save(self, name: str, policy: BasePolicy):
        assert mlflow.active_run() is not None
        zipped_name = f"{name}.zip"
        dir_path = Path(tempfile.mkdtemp())
        policy.save(dir_path / name)
        artifact_path = dir_path / zipped_name
        assert artifact_path.is_file()
        mlflow.log_artifact(artifact_path)
        shutil.rmtree(dir_path)

    def restore(self, name: str) -> Optional[BasePolicy]:
        zipped_name = f"{name}.zip"
        runs = self._get_all_runs()
        for run in runs:
            if run is None:
                continue
            artifacts_uri = run.info.artifact_uri
            if "file://" != artifacts_uri[:7]:
                raise Exception(f"Non-local artifacts path: {artifacts_uri}")
            artifacts_dir = Path(artifacts_uri[7:]).absolute()
            save_path = artifacts_dir / zipped_name
            if save_path.is_file():
                print(f"SB3Tracker: Restored SB3 PPO model '{name}'.")
                return PPO.load(save_path)
        print(f"SB3Tracker: No saved SB3 PPO '{name}' found.")
