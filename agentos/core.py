"""Core AgentOS APIs."""
from collections import namedtuple
import time
from threading import Thread


class Agent:
    """An Agent observes and takes actions in its environment till done.

    An agent holds an environment `self.env`, which it can use
    to observe and act by calling `self.env.step()` that takes
    an observation and returns an action.

    Like a human, an Agent lives in a stream of time. To to bring an
    Agent to life (i.e. have it exist and take actions in its
    environment), simply call agent.advance() repeatedly until
    that function returns True.

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
    def __init__(self, env_class):
        """Set self.env, then reset the env and store _last_obs."""
        self.env = env_class()
        self.init_obs = self.env.reset()
        self._init()

    def _init(self):
        """An alternative to overriding __init__ is override this.

        This is a convenience function for when you just want to
        add some functionality to the constructor but don't want
        to completely override the constructor.
        """
        pass

    def advance(self):
        """Returns True when agent is done; False or None otherwise."""
        raise NotImplementedError


class Policy:
    """Picks next action based on last observation from environment.

    Policies are used by agents to encapsulate any state or logic necessary
    to decide on a next action given the last observation from an env.
    """
    def compute_action(self, observation):
        """Takes an observation from an env and returns next action to take.

        :param observation: should be in the `observation_space` of the
                            environments that this policy is compatible with.
        :returns: action to take, should be in `action_space` of the
                            environments that this policy is compatible with.
        """
        raise NotImplementedError


def run_agent(agent_class, env, *args, hz=40, max_iters=None, as_thread=False, **kwargs):
    """Run an agent, optionally in a new thread.

    If as_thread is True, agent is run in a thread, and the
    thread object is returned to the caller. The caller may
    need to call join on that that thread depending on their
    use case for this agent_run.
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


"""
A rollout step function allows a developer to specify the behavior
that will occur at every step of the rollout, given a policy
and the last observation from the env, to decide
what action to take next. This usually involves the rollout's
policy and may perform learning and may involve using, updating,
or saving learning related state including hyper-parameters
such as epsilon in epsilon greedy.
"""
def default_rollout_step(policy, obs, step_num):
    return policy.compute_action(obs)


def rollout(policy, env_class, step_fn=default_rollout_step, max_steps=None):
    """ Perform rollout using env an with the type provided.

    :param policy: policy to use when simulating these episodes.
    :param env_class: class to instatiate an env object from.
    :param step_fn: a function to be called at each step of rollout.
                    The function can have 2 or 3 parameters.
                    2 parameter definition: policy, observation.
                    3 parameter definition: policy, observation, step_num.
                    The function must return an action.
    :param max_steps: cap on number of steps per episode.
    :return: the trajectory that was followed during this rollout.
             A trajectory is a named tuple that contains the initial
             observation (a scalar) as well as the following
             arrays: actions, observations, rewards, dones, contexts.
             The ith entry of each array corresponds to the action taken
             at the ith step of the rollout, and the respective results
             returned by the environment after taking that action.
             To learn more about the semantics of these, see the
             documentation and code of gym.Env.
    """
    actions = []
    observations = []
    rewards = []
    dones = []
    contexts =[]

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
            raise TypeError('step_fn must accept 2 or 3 parameters.')
        obs, reward, done, ctx = env.step(action)
        actions.append(action)
        observations.append(obs)
        rewards.append(reward)
        dones.append(done)
        contexts.append(ctx)
        step_num += 1
    Trajectory = namedtuple('Trajectory', ["init_obs", "actions", "observations", "rewards", "dones", "contexts"])
    return Trajectory(init_obs, actions, observations, rewards, dones, contexts)


def rollouts(policy,
             env_class,
             num_rollouts,
             step_fn=default_rollout_step,
             max_steps=None):
    """
    :param policy: policy to use when simulating these episodes.
    :param env_class: class to instatiate an env object from.
    :param num_rollouts: how many rollouts (i.e., episodes) to perform
    :param max_steps: cap on number of steps per episode.
    :return: array with one namedtuple per rollout, each tuple containing
             the following arrays: observations, rewards, dones, ctxs
    """
    return [rollout(policy, env_class, step_fn, max_steps)
            for _ in range(num_rollouts)]


