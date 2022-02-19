==================================
The Python Component System
==================================

The Python Component System (PCS) is an open source **Python API, command line
interface, and public web registry** for building, running, and sharing Python
programs.  The Python Component System is designed to:

  * Make program execution reproducible.

  * Transparently manage Python virtual environments and dependencies.

  * Simplify experiment tracking and code sharing.

The Python Component System is licensed under the Apache License, Version 2.0.


==================================
AgentOS
==================================

AgentOS is a set of libraries built on top of the Python Component System that
makes it easy to build, run, and share agents that use Reinforcement Learning
(RL) to solve tasks.

Key features of AgentOS:
  * Easy to use Agent API for developing and running new agents.

  * A `public repository <https://aos-web.herokuapp.com/#TODO>`_ of popular RL
    environments and agents, and runs of those agents in those environments
    that can be reproduced with a single line of code.

  * Example learning agents from different disciplines and research areas are
    available in the
    `example_agents
    <https://github.com/agentos-project/agentos/tree/master/example_agents>`_
    directory of the project source code.

.. image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions
  :alt: Test Status Indicator

AgentOS is beta software, APIs and overall architecture are likely to change
significantly over time.  AgentOS is licensed under the Apache License, Version
2.0.
