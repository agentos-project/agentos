=======================================
The Python Component System and AgentOS
=======================================

This project consists of two major pieces: the Python Component System (PCS)
and AgentOS.

Python Component System (PCS)
==================================

PCS is an open source **Python API, command line interface, and public web
registry** for building, running, and sharing Python programs.  PCS:

* Makes program execution reproducible.

* Transparently manages Python virtual environments while providing a Python
  API for ``pip`` and ``virtualenv``.

* Simplifies experiment tracking and code sharing.

PCS does this by allowing you to explicitly specify dependencies and parameters
for your program and then providing a thin runtime (currently based on `MLflow
<https://mlflow.org>`_) to automatically instrument your program's execution.
PCS is compatible with most frameworks that are used to build machine learning
and reinforcement learning systems.

AgentOS
==================================

AgentOS is a set of libraries built on top of the Python Component System that
make it easy to build, run, and share agents that use Reinforcement Learning
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

Connect
================

Ask questions or report bugs in PCS and AgentOS in
`GitHub Issues <https://github.com/agentos-project/agentos/issues>`_
or on the
`dev Discord <https://discord.gg/hUSezsejp3>`_.

Find the `AgentOS source code on Github <https://github.com/agentos-project/agentos>`_.

.. image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions
  :alt: Test Status Indicator



The Python Component System and AgentOS are alpha software; APIs and overall
architecture are likely to change significantly over time.  They are
licensed under the Apache License, Version 2.0.
