Install and Explore
===================
AgentOS requires Python >= 3.5. To get started, install agentos, and then run a
simple agent::

  # First make sure you're using python 3.5 or newer.
  pip install agentos
  agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv

Then, create and run your first Agent::

  mkdir my_agent
  cd my_agent
  agentos init
  agentos run

To see more complex agents, look at example agents in the `example_agents
<https://github.com/agentos-project/agentos/tree/master/example_agents>`_
directory of the project source code.
