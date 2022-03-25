**************
Example Agents
**************

.. _Lucida: https://github.com/claritylab/lucida
.. _MyCroft: https://github.com/MycroftAI/mycroft-core
.. _OpenCog: https://github.com/opencog/opencog
.. _RLkit: https://github.com/vitchyr/rlkit
.. _Soar: https://soar.eecs.umich.edu
.. _TensorForce: https://github.com/tensorforce/tensorforce


The ``example_agents`` directory of the `AgentOS source repository
<https://github.com/agentos-project/agentos/tree/master/example_agents>`_
contains examples of different types of learning agents built using PCS and the
AgentOS libraries.  

Most of these agents are built using RL frameworks from different research
teams illustrating the flexibility of PCS and AgentOS. Each of these agents has
a README describing how to run these agents.

The following example agents exist:

* A `DQN agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/acme_dqn>`_
  that plays CartPole (built using the `Acme RL framework
  <https://github.com/deepmind/acme>`_).

* An `R2D2 agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/acme_r2d2>`_
  that plays CartPole (built using the `Acme RL framework
  <https://github.com/deepmind/acme>`_).

* A `ChatBot agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/chatbot>`_

* A `Random agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/random>`_
  that randomly explores a 1D corridor.  This is the same agent that you get
  when you run ``agentos init .`` in a new directory.

* An `RLlib agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/rllib_agent>`_
  that plays CartPole (built using `Ray and RLlib
  <https://github.com/ray-project/ray>`_).

* A `PPO agent
  <https://github.com/agentos-project/agentos/tree/master/example_agents/sb3_agent>`_
  that plays CartPole (built using `Stable Baselines3
  <https://stable-baselines3.readthedocs.io/en/master/>`_).
