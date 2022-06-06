import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

import torch
from a2c_ppo_acktr import utils
from a2c_ppo_acktr.utils import get_vec_normalize

from agentos.agent_output import AgentRun


class PAPAGRun(AgentRun):
    """
    An PAPAGRun must be of type "learn" or "evaluate". Learning runs can have
    log_model() called on them.

    See the PyTorch A2C, PPO, ACKTR, and GAIL (PAPAG) repo here:

    https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail
    """

    PAPAG_RUN_TAG_KEY = "papag_agent_output"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_tag(self.PAPAG_RUN_TAG_KEY, "True")

    def log_model(self, name: str, actor_critic, envs):
        assert (
            self.run_type == "learn"
        ), "log_model can only be called by SB3Runs of type 'learn'"
        self.log_run_metrics()
        tmp_dir_path = Path(tempfile.mkdtemp())
        # see pytorch-a2c-ppo-acktr-gail/enjoy.py
        obs_rms = getattr(utils.get_vec_normalize(envs), "obs_rms", None)
        save_tuple = (actor_critic, obs_rms)
        artifact_path = tmp_dir_path / name
        assert not artifact_path.is_file()
        torch.save(save_tuple, artifact_path)
        assert artifact_path.is_file()
        self.log_artifact(artifact_path)
        shutil.rmtree(tmp_dir_path)

    def log_run_metrics(self):
        if self.episode_data:
            super().log_run_metrics()
        else:
            print("PAPAGRun: no episode data to log")

    @classmethod
    def _get_artifact_path(cls, mlflow_run_id: str, name: str) -> Path:
        return cls.MLFLOW_CLIENT.download_artifacts(mlflow_run_id, name)

    @classmethod
    def get_last_logged_model_run(cls, name: str) -> "PAPAGRun":
        runs = cls.MLFLOW_CLIENT.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.PAPAG_RUN_TAG_KEY} ILIKE "%"',
        )
        if runs:
            # Since runs is sorted by start_time descending, scan the list
            # for the first run that contains a policy by the name provided.
            for run in runs:
                try:
                    cls._get_artifact_path(run.info.run_id, name)
                except OSError:
                    continue  # No policy was logged in this run, keep trying.
                return PAPAGRun.from_existing_mlflow_run(run.info.run_id)
        return None

    @classmethod
    def get_last_logged_model(cls, name: str, envs) -> Optional[Any]:
        """
        Returns the most recent model that was logged by an PAPAGRun as an
        artifact with filename ``name``.
        :param name: the filename of the artifact to restore.
        :return: Most recently logged model, if one can be found, else None.
        """
        run = cls.get_last_logged_model_run(name)
        if run:
            print(f"PAPAGRun: Found last_logged policy '{name}'.")
            model_path = cls._get_artifact_path(run.mlflow_run_id, name)
            # We need the same stats for normalization as used in training
            actor_critic, obs_rms = torch.load(model_path, map_location="cpu")

            vec_norm = get_vec_normalize(envs)
            if vec_norm is not None:
                vec_norm.eval()
                vec_norm.obs_rms = obs_rms

            return actor_critic, obs_rms
        print(f"PAPAGRun: No policy with name '{name}' found.")
        return None, None
