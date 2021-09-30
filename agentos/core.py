"""Core AgentOS classes."""
from collections import namedtuple
from agentos.runtime import _check_path_exists
import statistics
import uuid
import shutil
from pathlib import Path
import pickle
import os


class MemberInitializer:
    """Takes all constructor kwargs and sets them as class members.

    For example, if MyClass is a MemberInitializer:

    a = MyClass(foo='bar')
    assert a.foo == 'bar'
    """

    @classmethod
    def ready_to_initialize(cls, shared_data):
        """Allows you to check shared_data for all your requirements before you
        get initialized"""
        return True

    def __init__(self, **kwargs):
        """Sets all the kwargs as members on the class"""
        for k, v in kwargs.items():
            setattr(self, k, v)


class Agent(MemberInitializer):
    """An Agent observes and takes actions in its Environment.

    The primary methods on an Agent are:

        * Agent.advance() - Takes on action within the Environment as
                            determined by the Agent's policy.
        * Agent.rollout() - Advances the Agent through one episode within its
                            Environment allowing it to gather experience and
                            learn.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.curr_obs = None
        self._should_reset = True

    def init(self, backing_dir):
        _check_path_exists(backing_dir)
        self.data_location = self._get_data_location(backing_dir)
        self.backing_dir = backing_dir
        os.makedirs(self._get_data_location(backing_dir), exist_ok=True)
        os.makedirs(self._get_backups_location(backing_dir), exist_ok=True)

    def advance(self):
        """Takes one action within the Environment as dictated by the Policy"""
        if self._should_reset:
            self.curr_obs = self.environment.reset()
            self._should_reset = False
            self.dataset.add(None, None, self.curr_obs, None, None, {})
        action = self.policy.decide(self.curr_obs)
        prev_obs = self.curr_obs
        self.curr_obs, reward, done, info = self.environment.step(action)
        self.dataset.add(prev_obs, action, self.curr_obs, reward, done, info)
        if done:
            self._should_reset = True
        return prev_obs, action, self.curr_obs, reward, done, info

    def rollout(self, should_learn, max_transitions=None):
        """Generates one episode of transitions and allows the Agent to
        learn from its experience.

        :param should_learn: if True, then Trainer.improve() will be called
                             every time the Agent advances one step through the
                             environment and the core training metrics
                             (transition_count and episode_count) will be
                             updated after the rollout.
        :param max_transitions: If not None, the episode and rollout will be
                                truncated after the specified number of
                                transitions.

        :returns: Number of transitions experienced in this episode.
        """
        done = False
        transition_count = 0
        while not done:
            if max_transitions and transition_count > max_transitions:
                self._episode_truncated()
                break
            _, _, _, _, done, _ = self.advance()
            transition_count += 1
            if should_learn:
                self.trainer.improve(self.dataset, self.policy)
        if should_learn:
            self.trainer.improve(self.dataset, self.policy)
            prev_transition_count = self.get_transition_count()
            new_transition_count = prev_transition_count + transition_count
            self.save_transition_count(new_transition_count)
            prev_episode_count = self.get_episode_count()
            self.save_episode_count(prev_episode_count + 1)
        return transition_count

    def reset_agent_directory(self, backing_dir, from_backup_id):
        _check_path_exists(backing_dir)
        if from_backup_id:
            restore_src = (
                self._get_backups_location(backing_dir) / from_backup_id
            )
            if not restore_src.exists():
                raise FileNotFoundError(
                    f"{restore_src.absolute()} does not exist!"
                )
        backup_dst = self._backup_agent(backing_dir)
        print(f"Current agent backed up to {backup_dst}.")
        data_location = self._get_data_location(backing_dir)
        shutil.rmtree(data_location)
        self._create_agent_directory_structure(backing_dir)
        if from_backup_id:
            print(restore_src)
            print(self._get_data_location(backing_dir))
            shutil.copytree(
                restore_src,
                self._get_data_location(backing_dir),
                dirs_exist_ok=True,
            )
            print(f"Agent state at {restore_src.absolute()} restored.")
        else:
            self._create_core_data(backing_dir)
            print("Agent state reset.")

    def _print_run_results(self, all_steps, backup_dst):
        if not all_steps:
            return
        mean = statistics.mean(all_steps)
        median = statistics.median(all_steps)
        print()
        print(f"Benchmark results after {len(all_steps)} rollouts:")
        print(
            "\tBenchmarked agent was trained on "
            f"{self.get_transition_count()} "
            f"transitions over {self.get_episode_count()} episodes"
        )
        print(f"\tMax steps over {len(all_steps)} trials: {max(all_steps)}")
        print(f"\tMean steps over {len(all_steps)} trials: {mean}")
        print(f"\tMedian steps over {len(all_steps)} trials: {median}")
        print(f"\tMin steps over {len(all_steps)} trials: {min(all_steps)}")
        if backup_dst:
            print(f"Agent backed up in {backup_dst}")
        print()

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

    def reset(self, from_backup_id):
        self.reset_agent_directory(
            backing_dir=self.backing_dir, from_backup_id=from_backup_id
        )

    def _backup_agent(self, data_dir):
        """Creates a snapshot of an agent at a given moment in time.

        :param data_dir: Directory path containing AgentOS components and data

        :returns: Path to the back up directory
        """
        data_dir = Path(data_dir).absolute()
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
        with open(self.data_location / name, "wb") as f:
            pickle.dump(data, f)

    def restore_data(self, name):
        with open(self.data_location / name, "rb") as f:
            return pickle.load(f)


class Policy(MemberInitializer):
    """Pick next action based on last observation from environment.

    Policies are used by Agents to encapsulate any state or logic necessary
    to decide on a next action given the last observation from an env.
    """

    def decide(self, observation):
        """Takes an observation and valid actions and returns next action to
        take.

        :param observation: should be in the `observation_space` of the
            environments that this policy is compatible with.
        :returns: action to take, should be in `action_space` of the
            environments that this policy is compatible with.
        """
        raise NotImplementedError


class Trainer(MemberInitializer):
    """The Trainer is responsible for improving the Policy of the Agent as
    experience is collected.

    The primary method on the Trainer is the improve() method which gets
    called for every step taken within the episode.  It is up to the
    particular implementation to decide if this tempo is appropriate for
    training.
    """

    def improve(self, dataset, policy):
        """This method updates the policy based on the experience in the
        dataset"""
        pass


class Dataset(MemberInitializer):
    """The Dataset is responsible for recording the experience of the Agent so
    that it can be used later for training.

    The primary methods on Dataset are:
        * add() - Adds a transition into the Dataset.
        * next() - Pulls a set of transitions from the Dataset for learning.
    """

    def add(self, prev_obs, action, curr_obs, reward, done, info):
        """Adds a transition into the Dataset"""
        pass

    # TODO - actually implement this in Acme/SB3 agents
    def next(self, *args, **kwargs):
        """Pulls a set of transitions from the Dataset for learning"""
        raise NotImplementedError


# Inspired by OpenAI's gym.Env
# https://github.com/openai/gym/blob/master/gym/core.py
class Environment(MemberInitializer):
    """Minimalist port of OpenAI's gym.Env."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "shared_data" in kwargs:
            shared_data = kwargs["shared_data"]
            shared_data["environment_spec"] = self.get_spec()
        self.action_space = None
        self.observation_space = None
        self.reward_range = None

    def step(self, action):
        """Perform the action in the environment."""
        raise NotImplementedError

    def reset(self):
        """Resets the environment to an initial state."""
        raise NotImplementedError

    def render(self, mode):
        raise NotImplementedError

    def close(self, mode):
        pass

    def seed(self, seed):
        raise NotImplementedError

    def get_spec(self):
        raise NotImplementedError


# https://github.com/deepmind/acme/blob/master/acme/specs.py
EnvironmentSpec = namedtuple(
    "EnvironmentSpec", ["observations", "actions", "rewards", "discounts"]
)
