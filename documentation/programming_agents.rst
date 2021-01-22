Programming Agents
==================

To develop an agent using AgentOS, the most important concepts are Agents, Policies, and Environments (or Envs).

An Agent is a class that can actions over time. It must have an environment. It can also have one or more Policy that it uses to make decisions

TODO: Why is is an agent required to have a class but not required to have a policy? Why not make the Agent API even more minimal and only require it have an advance function and leave it up to the agent developer to decide how the agent ends up with an env?


Environments
------------
Environments can be either simulators (e.g., CartPole) or connectors to the real world (e.g., an environment for a chatbot that passes messages back and forth between the agent and other agents, humans, etc.).

Environments must:

* Descend from gym.Env


Anatomy of an Agent
-------------------
There are very minimal requirements for AgentOS to recognize a Python class as an Agent.

And different agents should be able to perform wildly different types of tasks.

But we do expect Agents to be highly sophisticated. So then, how do we balannce these two competing design goals?


We make the base ``agentos.Agent`` class extremely minimal. To be compatible with AgentOS, an agent class must:

* Descend from agentos.Agent.
* Agents must take an environment class as the first argument to their __init__() function.
* Agents must define a instance function called ``advance()`` that returns a boolean.

And that's all of the requirements.

It is up to each agent developer how they want to structure the internals of their agent, but the only way that an agent can do anything is via its ``advance()`` is ho


Structure of ``advance`` function
---------------------------------
* Agents should 
* Decisions 


Background on design
--------------------
This design is inpired by operating systems where the core kernel code is kept minimal and most functionality is implemented in libraries (cite microkernels, exakernel).
