Install and Explore
===================

AgentOS requires Python 3.5 - 3.8 and `conda`. To get started, use pip to
install agentos, and then run a simple agent::

  # Make sure you're using Python 3.5 - 3.8
  # Make sure you have miniforge, miniconda, or conda installed (required
  # for `agentos run`, which uses MLflow Projects).
  pip install agentos
  agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv

Then, create and run your first Agent::

  mkdir my_agent
  cd my_agent
  agentos init
  agentos run

This type of agent is called an :doc:`Agent Directory <../agent_directories>`. To see more complex
agents, look at example agents in the `example_agents
<https://github.com/agentos-project/agentos/tree/master/example_agents>`_
directory of the project source code.
