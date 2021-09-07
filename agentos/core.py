"""Core AgentOS classes."""
from collections import namedtuple
from agentos.runtime import restore_data
from agentos.runtime import save_data


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

    An Agent holds the following pointers:

        * self.environment - The Environment with which the Agent interacts
        * self.policy - The Policy used to choose the Agent's next action
        * self.dataset - A Dataset to record the Agent's experience
        * self.trainer - A Trainer that updates the Policy based on the
                         Agent's experience

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

    def advance(self):
        """Takes one action within the Environment as dictated by the Policy"""
        if self._should_reset:
            self.curr_obs = self.environment.reset()
            self._should_reset = False
            self.dataset.add(None, None, self.curr_obs, None, None, {})
        action = self.policy.decide(
            self.curr_obs, self.environment.valid_actions
        )
        prev_obs = self.curr_obs
        self.curr_obs, reward, done, info = self.environment.step(action)
        self.dataset.add(prev_obs, action, self.curr_obs, reward, done, info)
        if done:
            self._should_reset = True
        return prev_obs, action, self.curr_obs, reward, done, info

    def rollout(self, should_learn):
        """Generates one episode of transitions and allows the Agent to
        learn from its experience.

        If the parameter <should_learn> is True, then Trainer.improve() will
        be called every time the Agent advances one step through the
        environment and the core training metrics (transition_count and
        episode_count)  will be updated after the rollout.
        """
        done = False
        transition_count = 0
        while not done:
            _, _, _, _, done, _ = self.advance()
            transition_count += 1
            if should_learn:
                self.trainer.improve(self.dataset, self.policy)
        if should_learn:
            prev_transition_count = self.get_transition_count()
            new_transition_count = prev_transition_count + transition_count
            self.save_transition_count(new_transition_count)
            prev_episode_count = self.get_episode_count()
            self.save_episode_count(prev_episode_count + 1)
        return transition_count

    def get_transition_count(self):
        """Gets the number of transitions the Agent has been trained on."""
        return restore_data("transition_count")

    def get_episode_count(self):
        """Gets the number of episodes the Agent has been trained on."""
        return restore_data("episode_count")

    def save_transition_count(self, transition_count):
        """Saves the number of transitions the Agent has been trained on."""
        return save_data("transition_count", transition_count)

    def save_episode_count(self, episode_count):
        """Saves the number of episodes the Agent has been trained on."""
        return save_data("episode_count", episode_count)


class Policy(MemberInitializer):
    """Pick next action based on last observation from environment.

    Policies are used by Agents to encapsulate any state or logic necessary
    to decide on a next action given the last observation from an env.
    """

    # FIXME - actions param unnecessary with environment specs
    def decide(self, observation, actions, should_learn=False):
        """Takes an observation and valid actions and returns next action to
        take.

        :param observation: should be in the `observation_space` of the
            environments that this policy is compatible with.
        :param actions: the action set from which the agent should choose.
        :param should_learn: should the agent learn from the transition?
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
