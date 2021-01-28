******************
Programming Agents
******************
.. contents:: Contents:
   :depth: 1
   :local:
.. _gym.Env: https://github.com/openai/gym/blob/master/gym/core.py

To develop an agent using AgentOS, the most important concepts to understand
are Agents, Policies, and Environments (or Envs).

An Agent is an entity that can take action over time. It must have an
environment. It can also have one or more Policy that it uses to make
decisions.

.. todo::

   Why is is an agent required to have an Env but not required to have a
   policy? Why not make the Agent API even more minimal and only require it
   have an advance function and leave it up to the agent developer to decide
   how the agent ends up with an env?



Environments
============
Environments can be either simulators (e.g., CartPole) or connectors to the
real world (e.g., an environment for a chatbot that passes messages back and
forth between the agent and other agents, humans, etc.).

AgentOS does not define its own Environment API, instead we reuse `gym.Env`_.
Environments must:

* Descend from ``gym.Env``.
* Define a function ``step(action) -> observation`` that takes an action and
  returns an observation.
* Define action and observation spaces.


Policies
========

In AgentOS, a Policy is a function that takes an observation as input and
returns an action. Policies must:

* Descend from ``AgentOS.Policy``.
* Define the ``compute_action(observation) -> action`` function.
* Define action and observation spaces.

.. todo::
   We should rename ``compute_action()`` to be something more concise and with
   semantics inspired by ``Env.step()``, such as ``decide()``.


Agents: putting it all together
================================
The architeture and API that AgentOS provides for Agents is minimal in order to
provide flexibility, because different agents should be able to perform very
different types of tasks. But it is also expected that Agents will be highly
sophisticated. So then most of the complexity of agents will be outside of
the core AgentOS abstraction (e.g., the ``agentos.Agent`` class).

To be compatible with AgentOS, an agent class must:

* Descend from ``agentos.Agent``.  Agents must take an environment class as the
* first argument to their
  ``__init__()`` function.
* Agents must define a instance function called ``advance()`` that returns a
  boolean.

That's it. It is up to each agent developer how they want to structure the
internals of their agent, but from AgentOS's perspective, the only way that an
agent can do anything is via its ``advance()`` function.


Guidelines for structuring ``advance()``
----------------------------------------
We recommend Agents keep the advance function as clean and minimal as possible,
with code living in other functions that are called with in the advance
function, or even better in other modules. Agent's are intended to be minimal
and easy to read, and mostly be used to import and compose functionality
contained in "agent libraries" (see :doc:`architecture_and_design`).


Background on agent design
--------------------------
This design is inspired by operating systems where the core kernel code is kept
minimal and most functionality is implemented in libraries (cite microkernels,
exakernel).


Rollouts
========
A rollout, also called an episode, is a concept that comes from Reinforcement
Learning. Conceptually, you can think of a rollout as a simulation of an agent
`advance()`-ing through time in order to learn.

Technically, a rollout is a process involving an instance of a
Policy and an instance of an Env that proceeds as demonstrated by the
following psuedocode:

.. code-block:: none

  def rollout(Env_class, Policy_class):
      """Psuedocode implementation of simplified rollout function.
      See agentos/core.py for the actual implementation."""
      env = get new instance of Env
      obs = initial observation from env
      policy = initialize a new Policy
      trajectory = []
      done = False
      until done:
          action = policy.compute_action(obs)
          obs, reward, done, _ = env.step(action)
          trajectory += [action, obs, reward]
      return trajectory

As you can see, performing a rollout generates a ``trajectory``, which you
can think of as a simulation of how an agent might advance through the given
environment, and what rewards it might receive along the way, if it were
to use the given policy.

Different types of agents and algorithms might use rollouts for
different purposes, but rollouts always consist of the same basic structure.

Since rollouts are used frequently and have a standard structure, AgentOS
includes the ``agentos.core.rollout()`` utility function.
