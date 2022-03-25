"""Core AgentOS classes."""
import time
from collections import namedtuple
from threading import Thread
from typing import Optional, Sequence

from agentos.agent_run import AgentRun


class MemberInitializer:
    """Takes all constructor kwargs and sets them as class members.

    For example, if MyClass is a MemberInitializer:

    a = MyClass(foo='bar')
    assert a.foo == 'bar'
    """

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.curr_obs = None
        self._should_reset = True
        self._active_agent_run_stack: Sequence[AgentRun] = []

    @property
    def active_agent_run(self) -> AgentRun:
        if self._active_agent_run_stack:
            return self._active_agent_run_stack[-1]
        else:
            return None

    def evaluate(
        self,
        num_episodes,
        should_learn=False,
        max_transitions=None,
        backup_dst=None,
        print_stats=True,
        parent_run=None,
    ) -> None:
        """Runs an agent specified by a given [agent_file]

        :param num_episodes: number of episodes to run the agent through
        :param should_learn: boolean, if True we will call policy.improve
        :param max_transitions: If not None, max transitions performed before
            truncating an episode.
        :param backup_dst: if specified, will print backup path to stdout
        :param print_stats: if True, will print run stats to stdout
        :param parent_run: If set, then the AgentRun created by this function
            will set this as their parent. Else, it will try to set the
            currently active component run, else it won't set a parent.

        :returns: None
        """
        all_steps = []
        if should_learn:
            self.start_agent_run("learn", parent_run)
        else:
            self.start_agent_run("evaluate", parent_run)
        for _ in range(int(num_episodes)):
            steps = self.rollout(
                should_learn=should_learn, max_transitions=max_transitions
            )
            all_steps.append(steps)
        print(f"print_stats is {print_stats}")
        print_results = (
            print_stats != "False"
            and print_stats != "false"
            and print_stats != "f"
        )
        self.end_agent_run(print_results=print_results)

    def learn(
        self,
        num_episodes,
        test_every,
        test_num_episodes,
        max_transitions=None,
    ) -> None:
        """Trains an agent by calling its learn() method in a loop."""
        num_episodes = int(num_episodes)
        test_num_episodes = int(test_num_episodes)
        # TODO: fix that ugliness!
        # Handle strings from -A
        if isinstance(test_every, str):
            if test_every == "True":
                test_every = True
            else:
                test_every = False
        test_every = int(test_every)
        run_size = test_every if test_every else num_episodes
        total_episodes = 0

        while total_episodes < num_episodes:
            if test_every:
                self.evaluate(
                    num_episodes=test_num_episodes,
                    should_learn=False,
                    max_transitions=max_transitions,
                    backup_dst=None,
                    print_stats=True,
                )
            self.evaluate(
                num_episodes=run_size,
                should_learn=True,
                max_transitions=max_transitions,
                backup_dst=None,
                print_stats=True,
            )
            total_episodes += run_size

    def start_agent_run(self, run_type: str, parent: AgentRun) -> None:
        from pcs import active_component_run  # avoid circular import

        if not parent:
            parent = active_component_run(self)
            if parent:
                assert self.environment.__component__
                assert self.environment.__component__ in (
                    parent.run_command.component.dependency_list()
                ), (
                    "This agent's environment must be in the dependency "
                    "list of the active component run."
                )
        self._active_agent_run_stack.append(
            AgentRun(run_type, parent_run=parent)
        )

    def end_agent_run(self, print_results: bool = False) -> None:
        assert self._active_agent_run_stack, "No active AgentRun to end."
        run = self._active_agent_run_stack.pop()
        run.end(print_results=print_results)

    def advance(self) -> None:
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

    def rollout(self, should_learn, max_transitions=None) -> int:
        """Generates one episode of transitions and allows the Agent to
        learn from its experience.

        :param should_learn: if True, then Trainer.improve() will be called
                             every time the Agent advances one step through the
                             environment and the core training metrics
                             (step_count and episode_count) will be
                             updated after the rollout.
        :param max_transitions: If not None, the episode and rollout will be
                                truncated after the specified number of
                                transitions.

        :returns: Number of transitions experienced in this episode.
        """
        done = False
        step_count = 0
        reward = 0
        while not done:
            if max_transitions and step_count > max_transitions:
                break
            _, _, _, tmp_reward, done, _ = self.advance()
            reward += tmp_reward
            step_count += 1
            if should_learn:
                self.trainer.improve(self.dataset, self.policy)
        self.active_agent_run.add_episode_data(steps=step_count, reward=reward)
        if should_learn:
            self.trainer.improve(self.dataset, self.policy)
        return step_count


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


class Environment(MemberInitializer):
    """
    An Env inspired by OpenAI's gym.Env and DM_Env
    https://github.com/openai/gym/blob/master/gym/core.py
    https://github.com/deepmind/dm_env/blob/master/docs/index.md
    """

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


class Runnable:
    def run(self, hz=40, max_iters=None, as_thread=False) -> Optional[Thread]:
        """
        Run an agent, optionally in a new thread.

        If as_thread is True, agent is run in a thread, and the
        thread object is returned to the caller. The caller may
        need to call join on that that thread depending on their
        use case for this agent_run.

        :param agent: The agent object you want to run
        :param hz: Rate at which to call agent's `advance` function. If None,
            call `advance` repeatedly in a tight loop (i.e., as fast as
            possible).
        :param max_iters: Maximum times to call agent's `advance` function,
            defaults to None.
        :param as_thread: Set to True to run this agent in a new thread,
            defaults to False.
        :returns: Either a running thread (if as_thread=True) or None.
        """

        def runner():
            done = False
            iter_count = 0
            while not done:
                if max_iters and iter_count >= max_iters:
                    break
                done = self.advance()
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
    The default rollout step function is the policy's ``decide`` function.
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
    return policy.decide(obs)


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
