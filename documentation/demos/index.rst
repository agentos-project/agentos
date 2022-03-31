***********************************
Demos
***********************************

Below are some python scripts that demonstrate using AgentOS to
run and share agents and environments from existing RL frameworks.


Stable Baselines 3
==================
In this demo, we infer a Registry automatically from the github repo
of a popular open source RL framework
(`Stable Baselines 3 <https://github.com/DLR-RM/stable-baselines3>`_, a fork of
OpenAI Baselines) and then create, run, and share a PPO agent Component from
that registry.

The following assumes you are running the AgentOS WebRegistry django server
app, which you can start via::

  # from within your agentos directory.
  python web/manage.py startserver 

Once you have the WebRegistry server running, try the following code:

.. include:: demo_script_sb3.py
   :literal:

PyTorch RL Algos by Ilya Kostrikov
==================================
**This demo is under construction.**

In this demo, we infer a Registry from the github repo of another popular
open source RL framework
(`Ilya Kostrikov's PyTorch A2C, PPO, ACKTR, and GAIL <https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail>`_)
and then create, run, and share a PPO agent from that registry.

.. include:: demo_script_ilya_ppo.py
   :literal:
