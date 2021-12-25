==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source **Python API, command line interface, and public web
registry** for building, running, and sharing learning agents. AgentOS is built
on the Python Component System, which implements a new programming model (the
Component Programming Model) that makes it easier to manage and share Python
code. AgentOS is licensed under the Apache License, Version 2.0.

Key features of the Python Component System are:
  * Transparent management of virtual environments (developers no longer
    have to think about virtual environments at all).

  * Decentralized Python dependency management

  * First-class programmatic access to all functionality (unlike PIP)

Key features of AgentOS include:
  * Easy to use Agent API for developing and running new agents.

  * A public repository of popular RL environments and agents, and
    runs of those agents in those environments that can be reproduced
    with a single line of code.

  * One existing agents* and benchmark runs of them,

  * Example learning agents from different disciplines and research areas are
    available in the
    `example_agents
    <https://github.com/agentos-project/agentos/tree/master/example_agents>`_
    directory of the project source code.

.. image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions
  :alt: Test Status Indicator

AgentOS is beta software, APIs and overall architecture are likely to change
significantly over time.
