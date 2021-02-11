"""Core AgentOS APIs."""
from collections import namedtuple
import time
from threading import Thread


class MemberInitializer:
    """Takes all constructor kwargs and sets them as class members.

    For example, if MyClass is a MemberInitializer:

    a = MyClass(foo='bar')
    assert a.foo == 'bar'
    """

    def __init__(self, **kwargs):
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

    def train(self):
        """Does one iteration of training"""
        raise NotImplementedError

    def advance(self):
        """Returns True when agent is done; False or None otherwise."""
        raise NotImplementedError


class Policy(MemberInitializer):
    """Pick next action based on last observation from environment.

    Policies are used by agents to encapsulate any state or logic necessary
    to decide on a next action given the last observation from an env.
    """

    def decide(self, observation):
        """Takes an observation and returns next action to take.

        :param observation: should be in the `observation_space` of the
            environments that this policy is compatible with.
        :returns: action to take, should be in `action_space` of the
            environments that this policy is compatible with.
        """
        raise NotImplementedError


class Trainer(MemberInitializer):
    """Mutates the agent's policy based on the agent's experience."""

    def train(self, policy, **kwargs):
        """Trains the policy.

        As the agent gains experience in the environment, Trainer.train updates
        the policy to reflect this experience so that the agent can maximize
        reward.

        :param policy: this is the current policy.  Train will mutate this
            in-place.

        :returns: updated policy
        """
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


def run_agent(
    agent_class, env, *args, hz=40, max_iters=None, as_thread=False, **kwargs
):
    """Run an agent, optionally in a new thread.

    If as_thread is True, agent is run in a thread, and the
    thread object is returned to the caller. The caller may
    need to call join on that that thread depending on their
    use case for this agent_run.

    :param agent_class: The class object of the agent you want to run
    :param env: The class object of the env you want to run the agent in.
    :param hz: Rate at which to call agent's `advance` function. If None,
        call `advance` repeatedly in a tight loop (i.e., as fast as possible).
    :param max_iters: Maximum times to call agent's `advance` function,
        defaults to None.
    :param as_thread: Set to True to run this agent in a new thread, defaults
        to False.
    :param \\*\\*kwargs: Other arguments to pass through to
           agent's `__init__()`.
    :returns: Either a running thread (if as_thread=True) or None.
    """

    def runner():
        agent_instance = agent_class(env, *args, **kwargs)
        done = False
        iter_count = 0
        while not done:
            if max_iters and iter_count >= max_iters:
                break
            done = agent_instance.advance()
            if hz:
                time.sleep(1 / hz)
            iter_count += 1

    if as_thread:
        t = Thread(target=runner)
        t.start()
        return t
    else:
        runner()


def default_rollout_step(policy, obs, step_num):
    """
    The default rollout step function is the policy's compute_action function.

    A rollout step function allows a developer to specify the behavior
    that will occur at every step of the rollout--given a policy
    and the last observation from the env--to decide
    what action to take next. This usually involves the rollout's
    policy and may perform learning. It also, may involve using, updating,
    or saving learning related state including hyper-parameters
    such as epsilon in epsilon greedy.

    You can provide your own function with the same signature as this default
    if you want to have a more complex behavior at each step of the rollout.
    """
    return policy.compute_action(obs)


def rollout(policy, env_class, step_fn=default_rollout_step, max_steps=None):
    """Perform rollout using provided policy and env.

    :param policy: policy to use when simulating these episodes.
    :param env_class: class to instantiate an env object from.
    :param step_fn: a function to be called at each step of rollout.
        The function can have 2 or 3 parameters, and must return an action:

        * 2 parameter definition: policy, observation.
        * 3 parameter definition: policy, observation, step_num.

        Default value is ``agentos.core.default_rollout_step``.

    :param max_steps: cap on number of steps per episode.
    :return: the trajectory that was followed during this rollout.
        A trajectory is a named tuple that contains the initial observation (a
        scalar) as well as the following arrays: actions, observations,
        rewards, dones, contexts. The ith entry of each array corresponds to
        the action taken at the ith step of the rollout, and the respective
        results returned by the environment after taking that action. To learn
        more about the semantics of these, see the documentation and code of
        gym.Env.
    """
    actions = []
    observations = []
    rewards = []
    dones = []
    contexts = []

    env = env_class()
    obs = env.reset()
    init_obs = obs
    done = False
    step_num = 0
    while True:
        if done or (max_steps and step_num >= max_steps):
            break
        if step_fn.__code__.co_argcount == 2:
            action = step_fn(policy, obs)
        elif step_fn.__code__.co_argcount == 3:
            action = step_fn(policy, obs, step_num)
        else:
            raise TypeError("step_fn must accept 2 or 3 parameters.")
        obs, reward, done, ctx = env.step(action)
        actions.append(action)
        observations.append(obs)
        rewards.append(reward)
        dones.append(done)
        contexts.append(ctx)
        step_num += 1
    Trajectory = namedtuple(
        "Trajectory",
        [
            "init_obs",
            "actions",
            "observations",
            "rewards",
            "dones",
            "contexts",
        ],
    )
    return Trajectory(
        init_obs, actions, observations, rewards, dones, contexts
    )


def rollouts(
    policy,
    env_class,
    num_rollouts,
    step_fn=default_rollout_step,
    max_steps=None,
):
    """
    :param policy: policy to use when simulating these episodes.
    :param env_class: class to instatiate an env object from.
    :param num_rollouts: how many rollouts (i.e., episodes) to perform
    :param step_fn: a function to be called at each step of each rollout.
                    The function can have 2 or 3 parameters.
                    2 parameter definition: policy, observation.
                    3 parameter definition: policy, observation, step_num.
                    The function must return an action.
    :param max_steps: cap on number of steps per episode.
    :return: array with one namedtuple per rollout, each tuple containing
             the following arrays: observations, rewards, dones, ctxs
    """
    return [
        rollout(policy, env_class, step_fn, max_steps)
        for _ in range(num_rollouts)
    ]
