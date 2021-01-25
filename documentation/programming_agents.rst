******************
Programming Agents
******************
.. _gym.Env: https://github.com/openai/gym/blob/master/gym/core.py>

To develop an agent using AgentOS, the most important concepts are Agents, Policies, and Environments (or Envs).

An Agent is an entity that can take action over time. It must have an environment. It can also have one or more Policy that it uses to make decisions.

.. todo:: 

   Why is is an agent required to have an Env but not required to have a policy? Why not make the Agent API even more minimal and only require it have an advance function and leave it up to the agent developer to decide how the agent ends up with an env?

.. contents:: Contents of this agent programming guide
   :depth: 1
   :local:


Environments
============
Environments can be either simulators (e.g., CartPole) or connectors to the real world (e.g., an environment for a chatbot that passes messages back and forth between the agent and other agents, humans, etc.).

AgentOS does not define its own Environment abstraction, instead we reuse `gym.Env`_. Environments must:

* Descend from ``gym.Env``.
* Define a function ``step(action) -> observation`` that takes an action and returns an observation.
* Define action and observation spaces.


Policies
========

In AgentOS, a policy is a function that takes an observation as input and returns an action. Policies must:

* Define the ``compute_action(observation) -> action`` function
* Define action and observation spaces.

.. todo::
   Should ``compute_action()`` be renamed something more concise and with semantics
   inspired by ``Env.step()``, such as ``decide()``?


Agents: putting it all together
================================
There are very minimal requirements for AgentOS to recognize a Python class as an Agent.

And different agents should be able to perform wildly different types of tasks.

But we do expect Agents to be highly sophisticated. So then, how do we balannce these two competing design goals?


We make the base ``agentos.Agent`` class extremely minimal. To be compatible with AgentOS, an agent class must:

* Descend from ``agentos.Agent``.
* Agents must take an environment class as the first argument to their __init__() function.
* Agents must define a instance function called ``advance()`` that returns a boolean.

And that's all of the requirements.

It is up to each agent developer how they want to structure the internals of their agent, but the only way that an agent can do anything is via its ``advance()`` is ho


Guidelines for structuring ``advance()``
----------------------------------------
We recommend Agents keep the advance function as minimal as possible


Background on agent design
--------------------------
This design is inspired by operating systems where the core kernel code is kept minimal and most functionality is implemented in libraries (cite microkernels, exakernel).


Rollouts
========
A rollout, also called an episode, is a concept that comes from Reinforcement Learning. A rollout is a simulation of an agent `advance()`-ing through time in order to learn. Different types of agents and algorithms might use rollouts for different purposes, but they always consist of the same basic structure.

Since rollouts are used frequently and have a standard structure, AgentOS includes the ``agentos.core.rollout()`` utility function.
