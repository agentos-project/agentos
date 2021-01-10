************************
Architecture and Design
************************

Background from Reinforcement Learning
======================================

In Reinforcement Learning (RL), the basic control loop is between agent and
environment, as shown in :numref:`fig_trad_rl_arch`. An environment (or env) is
a stateful object analogous to a simplified version of the world we live in. In
a programming language, an Env (e.g., OpenAI’s gym.Env) is often an object with
a ``step()`` function that takes an action and returns an observation (or
“state”) and reward.

An agent encapsulates the ability to make a decision and act in that env. An
agent usually contains a policy which is a function that takes an (observation,
reward) pair and returns an action.

.. _fig_trad_rl_arch:
.. figure:: traditional_rl_agent_arch.png
  :width: 80%
  :align: center

  The traditional RL view of the loop between Agent (green) and Environment
  (blue). The information that passes between them at a given time step t
  includes: action A\ :subscript:`t`, state (a.k.a, observation)
  S\ :subscript:`t`, and reward R\ :subscript:`t`.  Image modified from `Sutton &
  Barto <http://incompleteideas.net/book/the-book-2nd.html>`_ figure 3.1 (pg
  48).

.. _fig_agentos_agent_arch:
.. figure:: agentos_agent_arch.png
  :width: 80%
  :align: center

  The concepts are very similar in AgentOS, though AgentOS also differentiates
  between an agent and a policy, and formalizes the relationship between agent,
  policy, and environment: an agent has a policy and an environment connected
  in a message passing loop. Calling ``agent.advance()`` causes a single
  iteration of that loop to occur.


AgentOS Concepts
===================

The RL concepts of an **agent** and its **environment**, as described above are
very similar to those in AgentOS. However, AgentOS differs from the classic RL
architecture in a few key ways. First, an agent is paired with -- and holds a
reference to -- its environment. Second, the agent also can hold a policy.
Finally, the agent has an ``advance()`` function, inside of which it takes one
step around the core RL loop between the agent’s policy and its environment.

In terms of design philosophy, environments, policies, and agents are:

  * *Stateful* - an environment tracks internal state (e.g. location of objects
    in a room), a policy often maintains a machine learning model which can be
    updated to reflect past learnings; an agent maintains a policy, an
    environment, as well as arbitrary other state (e.g. recent observations
    from its env, memory modules, etc.);

  * *Flexible and minimal* - minimal APIs result in minimal constraints on
    developers. For example, developers can choose their own concurrency model,
    architecture, algorithms, etc.

The following are high-level descriptions of key AgentOS concepts.

**AgentOS**. A project that contains tools, APIs, and conventions for building,
managing, and sharing learning agents.

**Environment**. Environments have ``step()`` and ``reset()`` functions as they
are defined in ``gym.Env``. We recommend making a class that inherits from
``gym.Env``.

**Policy**. Policies have a ``compute_action()`` function which the agent can
use to decide on their next action, given the most recent observation returned
from the agent’s environment.

**Agent**. A Python class that has an ``advance()`` function that returns a
boolean, and encapsulates the agent behavior necessary to take steps in its
environment:

  * choose actions (e.g. a policy)

  * takes actions by calling ``self.env.step()``

  * learn from -- or otherwise updates internal state based on -- return value
    of ``self.env.step()``

AgentOS provides ``agentos.Agent`` as a reference implementation of an abstract
agent base class. A running agent is called an agent instance.

**Agent Runner**.  Code that runs an agent by calling ``agent.advance()`` till
it returns ``True``. It might also instantiate the agent (or it might take an
agent instance).

**CLI**. The Command Line Interface provides some basic commands for creating
and running an AgentOS agent, mostly for learning AgentOS.

**Agent directory**. A directory with standard files needed by AgentOS CLI to
create or run an agent using MLflow. Also known as agent project.


Architecture
=============

:numref:`fig_architecture` shows the main AgentOS architectural components.

.. _fig_architecture:
.. figure:: architecture.png
  :alt: AgentOS architecture
  :align: center

  The basic architecture of Agentos.


Modes of Interacting with AgentOS
=================================

Agents, policies, environments, etc. are written in Python. Agent instances can
be run via Python in scripts or interactively with ``agentos.run_agent()`` or
via the CLI.

The CLI supports a few basic commands:
  * ``agentos init`` - create files that define an example agent in the current
    directory.

  * ``agentos run`` - run an agent. Supports a few convenient ways to specify
    the agent class and env class that make up the agent instance. If called
    without any args, tries to run the current dir as an MLflow project, else
    looks for agent and env class definitions in agent.py. Under the hood,
    regardless of which argument option is used, ``agentos.run_agent()`` is
    called. See the pydocs for full details.



