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
    """An Agent observes and takes actions in its environment till done.

    An agent holds an environment ``self.env``, which it can use
    to observe and act by calling ``self.env.step()`` that takes
    an observation and returns an action.

    Like a human, an Agent lives in a stream of time. To to bring an
    Agent to life (i.e. have it exist and take actions in its
    environment), simply call agent.advance() repeatedly until
    that function returns True (which means the agent is done).

    The agent can maintain any sort of state (e.g., a policy for
    deciding its next action), but any use or updates of state must
    happen from within the agent's advance() function (which itself can
    be arbitrarily complex, call other functions, etc.).

    Often, an agent's advance function has 3 phases:

        1) pre-action
        2) take action and save observation
        3) post-action

    ...with phases 1 and 3 often including internal decision making,
    learning, use of models, state updates, etc.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.curr_obs = None
        self._should_reset = True

    def step(self):
        """Takes one action within the environment"""
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
        """Does training on one rollout worth of transitions"""
        done = False
        step_count = 0
        while not done:
            _, _, _, _, done, _ = self.step()
            step_count += 1
            if should_learn:
                self.trainer.improve(self.dataset, self.policy)
        if should_learn:
            prev_step_count = self.get_step_count()
            prev_episode_count = self.get_episode_count()
            self.save_step_count(prev_step_count + step_count)
            self.save_episode_count(prev_episode_count + 1)
        return step_count

    def advance(self):
        """Returns True when agent is done; False or None otherwise."""
        raise NotImplementedError

    def get_step_count(self):
        return restore_data("step_count")

    def get_episode_count(self):
        return restore_data("episode_count")

    def save_step_count(self, step_count):
        return save_data("step_count", step_count)

    def save_episode_count(self, episode_count):
        return save_data("episode_count", episode_count)


class Policy(MemberInitializer):
    """Pick next action based on last observation from environment.

    Policies are used by agents to encapsulate any state or logic necessary
    to decide on a next action given the last observation from an env.
    """

    # FIXME - actions param unnecessary with environment specs
    def decide(self, observation, actions, should_learn=False):
        """Takes an observation and returns next action to take.

        :param observation: should be in the `observation_space` of the
            environments that this policy is compatible with.
        :param actions: the action set from which the agent should choose.
        :param should_learn: should the agent learn from the transition?
        :returns: action to take, should be in `action_space` of the
            environments that this policy is compatible with.
        """
        raise NotImplementedError


class Trainer(MemberInitializer):
    def improve(self, dataset, policy):
        pass


class Dataset(MemberInitializer):
    def add(self, prev_obs, action, curr_obs, reward, done, info):
        pass

    # TODO - actually implement this in Acme/SB3 agents
    def next(self, *args, **kwargs):
        raise NotImplementedError


# Inspired by OpenAI's gym.Env
# https://github.com/openai/gym/blob/master/gym/core.py
class Environment(MemberInitializer):
    """Minimalist port of OpenAI's gym.Env."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
