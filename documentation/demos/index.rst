***********************************
Demos
***********************************

Below are some python scripts that demonstrate using AgentOS to
run and share agents and environments from existing RL frameworks.

Several of the the following demo scripts assume you are running the
AgentOS WebRegistry django server app, which you can start via::

  # from within your agentos directory.
  python web/manage.py startserver

AgentOS example SB3 agent from registry file in Github
======================================================
In this demo, we create an agent Module from a registry file that
exists in our local clone of the AgentOS github repo. Then we auto-convert
the agent Module from an unversioned Module to a versioned Module.
Then we run that agent and publish the run to a local WebRegistry.

Assuming you have the WebRegistry server running, try the following code:

.. include:: demo_script_sb3_example_agent.py
   :literal:

AgentOS example random agent from Github manually assembled
===========================================================
This demo is similar to the previous one except instead of loading an
agent from a registry file that exists in the AgentOS Github repo,
we manually compose an agent out of components that we fetch from
the AgentOS github repo. Then we run that agent and publish the run to
a local WebRegistry. Finally, it fetches the run back in from the
local WebRegistry and re-runs it.

Assuming you have the WebRegistry server running, try the following code:

.. include:: demo_script_agentos_github_random_agent.py
   :literal:

Module from registry auto-inferred directly from Stable Baselines 3 Github
=============================================================================
In this demo, we infer a Registry automatically from the github repo
of a popular open source RL framework
(`Stable Baselines 3 <https://github.com/DLR-RM/stable-baselines3>`_, a fork of
OpenAI Baselines) and then create, run, and share a PPO agent Module from
that registry.

Assuming you have the WebRegistry server running, try the following code:

.. include:: demo_script_sb3_single_component_inferred.py
   :literal:

[Work In Progress] PyTorch RL Algos by Ilya Kostrikov
=====================================================
**This demo is under construction.**

In this demo, we infer a Registry from the github repo of another popular
open source RL framework
(`Ilya Kostrikov's PyTorch A2C, PPO, ACKTR, and GAIL <https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail>`_)
and then create, run, and share a PPO agent from that registry.

.. include:: demo_script_ilya_ppo.py
   :literal:
