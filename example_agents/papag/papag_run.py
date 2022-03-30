import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

import torch
from a2c_ppo_acktr import utils
from a2c_ppo_acktr.utils import get_vec_normalize

from agentos.agent_run import AgentRun


class PAPAGRun(AgentRun):
    """
    An PAPAGRun must be of type "learn" or "evaluate". Learning runs can have
    log_model() called on them.

    See the PyTorch A2C, PPO, ACKTR, and GAIL (PAPAG) repo here:

    https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail
    """

    PAPAG_RUN_TAG_KEY = "papag_agent_run"

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
            environment_name=environment_name,
        )
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
    def get_last_logged_model(cls, name: str, envs) -> Optional[Any]:
        """
        Returns the most recent model that was logged by an PAPAGRun as an
        artifact with filename ``name``.
        :param name: the filename of the artifact to restore.
        :return: Most recently logged model, if one can be found, else None.
        """
        runs = cls._mlflow_client.search_runs(
            experiment_ids=[cls.DEFAULT_EXPERIMENT_ID],
            order_by=["attribute.start_time DESC"],
            filter_string=f'tag.{cls.PAPAG_RUN_TAG_KEY} ILIKE "%"',
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
                print(f"PAPAGRun: Found last_logged policy '{name}'.")
                # We need to use the same statistics for normalization as
                # used in training
                actor_critic, obs_rms = torch.load(
                    policy_path, map_location="cpu"
                )

                vec_norm = get_vec_normalize(envs)
                if vec_norm is not None:
                    vec_norm.eval()
                    vec_norm.obs_rms = obs_rms

                return actor_critic, obs_rms
        print(f"PAPAGRun: No policy with name '{name}' found.")
        return None, None
