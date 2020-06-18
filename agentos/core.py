"""Core AgentOS APIs."""
import time
from threading import Thread


class Agent:
    """An Agent observes and takes actions in its environment till done.

    An agent holds an environment `self.env`, which it can use
    to observe and act by calling `self.env.step()` that takes
    an observation and returns an action.

    Like a human, an Agent lives in a stream of time. To to bring an
    Agent to life (i.e. have it exist and take actions in its
    environment), simply call agent.step() repeatedly until
    that function returns True.

    The agent can maintain any sort of state (e.g., a policy for
    deciding its next action), but any use or updates of state must
    happen from within the agent's step() function (which itself can
    be arbitrarily complex, call other functions, etc.).

    Often, an agent's step function has 3 phases:
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

    def step(self):
        """Returns True when agent is done."""
        raise NotImplementedError

    def simulate_episodes(self, policy, num_simulations, max_steps=None):
        """ Simulate episodes (rollouts) using envs with same type as self.env.

        :param policy: policy to use when simulating these episodes.
        :param num_simulations: how many simulations to perform
        :param max_steps: cap on number of iterations per episode.
        :return: array of return values from episodes.
        """
        return_vals = [0] * num_simulations
        for i in range(num_simulations):
            env = self.env.__class__()
            obs = env.reset()
            step_num = 0
            done = False
            while True:
                if done or (max_steps and step_num >= max_steps):
                    break
                obs, reward, done, _ = env.step(policy.compute_action(obs))
                return_vals[i] += reward
                step_num += 1
        return return_vals

    def simulate_episode(self, policy):
        """Convenience wrapper of simulate_episodes for single-rollout case."""
        return self.simulate_episodes(policy, 1)


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


def run_agent(agent_class, env, hz=40, max_steps=None, as_thread=False, **kwargs):
    """Run an agent, optionally in a new thread.

    If as_thread is True, agent is run in a thread, and the
    thread object is returned to the caller. The caller may
    need to call join on that that thread depending on their
    use case for this agent_run.
    """
    def runner():
        agent_instance = agent_class(env, **kwargs)
        done = False
        step_count = 0
        while not done:
            if max_steps and step_count >= max_steps:
                break
            done = agent_instance.step()
            time.sleep(1 / hz)
            step_count += 1
    if as_thread:
        return Thread(target=runner).start()
    else:
        runner()
