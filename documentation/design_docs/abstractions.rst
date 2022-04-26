=========================
AgentOS Core Abstractions
=========================

Current Version: v4

See `Revision History`_ for additional discussion.


Abstract
========

This document proposes the core abstractions of the AgentOS system.  These
abstractions are:

* **Environment** - A representation of the world in which the agent operates.
  An agent takes actions within an environment, and these actions can
  potentially affect the environment's state (and thus the agent's
  observation).

* **Policy** - Encapsulates the agent's decision making process.  The policy
  chooses an action given a set of observations.  It also provides facilities
  for improving itself as the agent gains experience.

* **Agent** - The agent contains a policy.  It performs actions based on its
  policy within the environment so that it can learn how to maximize reward.

Rationale
=========

AgentOS aims to define a clean set of abstractions that will be familiar to a
researcher in the reinforcement learning (RL) space while also being
approachable to a technically educated generalist like a software engineer.
The proposed set of abstractions hew closely to the standard academic
presentation of RL while allowing for composition and reuse at the software
level.


User Stories
============

RL newbie trying to learn
-------------------------

As a software programmer and newbie to RL/AI, I want learn RL by looking at
documentation and code examples and I want to start making my own agents by
composing existing algorithms, environments, etc. I am interested in using both
the AgentOS CLI and the Python API as I learn.


Agent developer using Python
----------------------------

As an agent developer, I want to write my own agents, policies, environments,
and other components from scratch in Python and manipulate them entirely via
the command line.


Agent user running somebody elses agent
---------------------------------------

As a researcher on a conference program committee reviewing RL papers, I want
to clone my own copy of an agent from a paper, run it, and inspect its parts.
Ideally I would like it to conform to known APIs so that I can a priori have
some idea of what different parts do.

Agent developer incorporating RL into their tech stack
------------------------------------------------------

As a developer incorporating RL into my tech stack, I need to run experiments
with different agent configurations to determine what flavor of RL is best
suited to the business problem my work is addressing. Being able to
programmatically interact with agents allows me to run these experiments as
well as train and deploy my agent in a reproducible way.


Core Abstractions
=================

This section will present sample code for each of the core abstractions as
well as discuss implications and future directions.

Environment
-----------

An environment will conform to `OpenAI's gym <https://gym.openai.com/>`_ API.
Core methods are:

* ``step(action) -> (observation, done, reward, info)``: This takes one action
  within the environment and transitions to a new state.

* ``reset() -> observation``: This resets the environment to an initial state.

Here is an example environment that represents a 1-dimensional corridor that
the agent must learn to walk down::

    import gym

    class Corridor(gym.Env):

        def __init__(self):
            self.length = 10
            self.action_space = gym.spaces.Discrete(2)
            self.observation_space = gym.spaces.Discrete(self.length + 1)
            self.reset()

        def step(self, action):
            assert action in [0, 1]
            if action == 0:
                self.position = max(self.position - 1, 0)
            else:
                self.position = min(self.position + 1, self.length)
            return (self.position, -1, self.done, {})

        def done(self):
            return self.position >= self.length

        def reset(self):
            self.position = 0
            return self.position

Policy
------

A policy encapsulates an agent's decision making process.  A policy will often
be backed by some sort of stateful storage (e.g. a table or a serialized
neural net).  Eventually, AgentOS will provide ability to easily share
policies (including their state) between agents.

A policy must provide the following three methods:

* ``decide(self, obs) -> action``: Takes the agent's current observation and
  returns the next action the agent should take.

* ``improve(self, **kwargs) -> None``: Updates the agent's policy based upon
  experience (e.g. training the DQN backing the policy via gradient descent).

* ``reset(self) -> None``: Dumps any stateful part of the policy so that the
  agent can restart learning from scratch.


An example policy class might look like the following::

    import agentos

    class DeepQNetwork(agentos.Policy):
        def decide(self, obs):
            action_probabilites = self.nn(obs)
            return random.weighted_choose(action_probabilities)

        def improve(self, environment_class):
            rollouts = agentos.do_rollouts(self, environment_class)
            advantaged_rollouts = calculate_advantage(rollouts)
            self.nn.train(advantaged_rollouts)

        def reset(self):
            self.nn = create_new_neural_net()

Agent
-----

An agent is the entity that performs actions within the environment based on
its policy.  An agent provides the following methods:

* ``learn() -> None``: This is called to improve the agent's policy via
  practice within the environment.


* ``advance() -> None``: This is called to cause the agent to act within its
  environment based on its current policy.

The base agent class is defined as follows::

    class Agent:
        def __init__(self, policy, trainer, environment):
            self.policy = policy
            self.trainer = trainer
            self.environment = environment

        def learn():
            pass

        def advance():
            raise NotImplementedError

An example agent class might look like the following::

    import agentos

    class MyAgent(agentos.Agent):
        def learn(self):
            self.policy.improve()

        def advance(self):
            next_action = self.policy.decide(self.obs)
            self.obs, done, reward, info  = self.environment.step(next_action)


Note that ``learn()`` will be a no-op for some agents as the their learning
might take place while the agent is advancing through its environment.  To
this end, we propose two common subclasses of the agent:

* ``OnlineAgent``: This agent learns while it advances through its
  environment.  Thus ``learn()`` will often be a no-op as the policy will be
  trained each time ``advance()`` gets called.

* ``BatchAgent``: This agent learns in an "offline" manner.  It will either
  record its various trajectories through the environment or practice in an
  isolated instantiation of its environment.  This agent's policy will only be
  trained when ``train()`` is called.


Agent Definition File
---------------------

Every agent will define an ``agent.ini`` file that describes the specific
components of the agent.  A standard agent directory structure might look
something like the following::

    my_agent/
      - main.py
      - environment.py
      - policy.py
      - policy/
        - serialized_nn.out
      - agent.ini

Combining our example code from above, our agent's ``agent.ini`` file will
look like the following::

      [Agent]
      file_path = agent.py
      class_name = MyAgent
      python_path = ./

      [Policy]
      file_path = policy.py
      class_name = DeepQNetwork
      python_path = ./
      architecture = [10,100,100]
      buffer_size = 10000
      batch_size = 100
      storage = ./policy/

      [Environment]
      file_path = environment.py
      class_name = Corridor
      python_path = ./



Note that the ``agent.ini`` contains both the location of the primary
components of the agent as well as various configuration variables and
hyperparameters.  This file will be managed by the AgentOS Module Registry
(ACR) to allow for easy composition and reuse of AgentOS components.  It is
also human readable and editable, if the developer wants to directly modify
it.

The policy and environment will be accessible within the agent class as
``self.policy`` and ``self.environment`` respectively.


Demo
====

AgentOS will provide both command line and programmatic access to agents.

A common use case will be using the command-line to train and run an agent as
follows::


    agentos train agent.ini 1000   # Train the agent's policy over 1000 rollouts
    agentos run agent.ini          # Run our agent to measure performance
    agentos train agent.ini 1000   # Train our agent on another 1000 rollouts
    agentos run agent.ini          # Measure performance again
    agentos reset agent.ini        # Resets the agent's policy; forget all learning


The AgentOS CLI provides several ways to run an agent.  You can run using the
components specified in the ``agent.ini`` in the current directory as
follows::

    agentos run

Alternatively, you can specify the ``agent.ini`` file to use as follows::

    agentos run -f ../../agent.ini

Finally, you can specify all the components of an agent individually as
follows::

    agentos run -e myenv.Env -p mypolicy.Policy -a main.MyAgent


Additionally, AgentOS provides methods for running agents programmatically
either using an ``agent.ini`` file::

    agentos.run_agent_file('path/to/file/agent.ini')

Or by specifying each component as a keyword argument::

    agentos.run_agent(
        agent=MyAgent,
        environment=MyEnv,
        policy=MyPolicy,
    )

Long Term Plans
===============

* Mark core classes and methods as abstract as appropriate.  See `Abstract
  Base Classes (ABCs) <https://docs.python.org/3/library/abc.html>`_ and `the
  ABC PEP <https://www.python.org/dev/peps/pep-3119/>`_.

* Separate out a Reward abstraction from the Environment abstraction.



Revision History
================

* Discussion Thread:

  * `Design of Core Abstractions <https://github.com/agentos-project/design_docs/discussions/5>`_

* Pull requests:

  * `design_docs #3: AgentOS Core Abstractions <https://github.com/agentos-project/design_docs/pull/3>`_

* Document version history:

  * `v1 <https://github.com/agentos-project/design_docs/blob/f94af06f8fc66f867ca07bf7273d39d185489251/abstractions.rst>`_

  * `v2 <https://github.com/agentos-project/design_docs/blob/8ea7544c9edc47c1dedd992ba95e9dafeed33b36/abstractions.rst>`_

    * Added code for Agent base class

    * Fixed ``policy()`` function signature to return ``None``

    * Minor rework of description of core abstractions

  * `v3 <https://github.com/agentos-project/design_docs/blob/640f71509c7551b335e6312822392069b6e8c8e9/abstractions.rst>`_

    * Drop Trainer abstraction in favor of `Policy.improve()`

    * Rename `agent.train` to `agent.learn`

    * Default implementation of `Agent.learn` is no-op

    * Default implementation of `Agent.advance` is NotImplementedError

    * Added long-term plans section

  * `v4 <https://github.com/agentos-project/design_docs/blob/271b7450c0d1c50540f170857d9a6357acbd8fd7/abstractions.rst>`_

    * Added user stories

    * Updated ``agent.ini`` example
