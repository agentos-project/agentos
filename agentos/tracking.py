import os
import pickle
from pathlib import Path
import shutil
import uuid


class Tracker:
    def __init__(self, backing_dir):
        self.backing_dir = backing_dir
        self._create_backing_directory_structure()
        self._create_core_data()

    def reset(self, from_backup_id):
        if from_backup_id:
            restore_src = (
                    self._get_backups_location(self.backing_dir) / from_backup_id
            )
            if not restore_src.exists():
                raise FileNotFoundError(
                    f"{restore_src.absolute()} does not exist!"
                )
        backup_dst = self._backup_agent(self.backing_dir)
        print(f"Current agent backed up to {backup_dst}.")
        data_location = self._get_data_location(self.backing_dir)
        shutil.rmtree(data_location)
        self._create_backing_directory_structure()
        if from_backup_id:
            print(restore_src)
            print(self._get_data_location(self.backing_dir))
            shutil.copytree(
                restore_src,
                self._get_data_location(self.backing_dir),
                dirs_exist_ok=True,
            )
            print(f"Agent state at {restore_src.absolute()} restored.")
        else:
            self._create_core_data()
            print("Agent state reset.")

    def _create_backing_directory_structure(self):
        os.makedirs(self.backing_dir, exist_ok=True)
        os.makedirs(self._get_data_location(self.backing_dir), exist_ok=True)
        os.makedirs(self._get_backups_location(self.backing_dir), exist_ok=True)

    def _create_core_data(self):
        self.save_data("transition_count", 0)
        self.save_data("episode_count", 0)

    def _episode_truncated(self):
        # TODO - record truncations to improve training?
        # See truncation() in
        # https://github.com/deepmind/dm_env/blob/master/dm_env/_environment.py
        pass

    def get_transition_count(self):
        """Gets the number of transitions the Agent has been trained on."""
        return self.restore_data("transition_count")

    def get_episode_count(self):
        """Gets the number of episodes the Agent has been trained on."""
        return self.restore_data("episode_count")

    def save_transition_count(self, transition_count):
        """Saves the number of transitions the Agent has been trained on."""
        return self.save_data("transition_count", transition_count)

    def save_episode_count(self, episode_count):
        """Saves the number of episodes the Agent has been trained on."""
        return self.save_data("episode_count", episode_count)

    def _backup_agent(self, data_dir=None):
        """Creates a snapshot of an agent at a given moment in time.

        :param data_dir: Directory path containing AgentOS components and data.
            If not provided, use this tracker's `backing_dir` attribute.

        :returns: Path to the back up directory
        """
        if data_dir:
            data_dir = Path(data_dir).absolute()
        else:
            data_dir = self.backing_dir
        data_location = self._get_data_location(data_dir)
        backup_dst = self._get_backups_location(data_dir) / str(uuid.uuid4())
        shutil.copytree(data_location, backup_dst)
        print("done backing up agent network")
        return backup_dst

    def _get_data_location(self, backing_dir):
        return Path(backing_dir).absolute() / "data"

    def _get_backups_location(self, backing_dir):
        return Path(backing_dir).absolute() / "backups"

    def save_data(self, name, data):
        with open(self._get_data_location(self.backing_dir) / name, "wb") as f:
            pickle.dump(data, f)

    def restore_data(self, name):
        with open(self._get_data_location(self.backing_dir) / name, "rb") as f:
            return pickle.load(f)
