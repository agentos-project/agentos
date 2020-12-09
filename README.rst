==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source python API and a command line interface for building, running, and sharing learning agents. AgentOS is licensed under the Apache License, Version 2.0.

|Tests Status|

.. |Tests Status| image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions)
  :alt: Test Status Indicator

Requires Python >= 3.5 (because the CLI uses pathlib)


Install and try it out
----------------------
To install::

  git clone git@github.com:agentos-project/agentos.git
  pip install -e agentos # you may want to do this inside a virtualenv or conda env.

Then run a simple agent that comes with AgentOS::

  cd agentos
  agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv

Then, maybe create your first Agent::

  mkdir my_agent
  cd my_agent
  agentos init
  # optionally edit ./conda_env.yaml so that `agentos` dependency points to your install of agentos
  # else the command below will use agentos from PyPI.
  agentos run

Also, check out the example agents in the `example_agents` directory.

Learn more and see the docs at `agentos.org <https://agentos.org>`_.


Tests
-----
To run tests::

  pip install -r test-requirements.txt
  pytest all_tests.py


Building Documentation
----------------------
To build the docs you'll need to install and use `jekyll <https://jekyllrb.com/>`_::

  gem install jekyll bundler twine
  cd docs
  bundle exec jekyll serve


Pushing to PyPI
---------------
To push a release to PyPI, follow `these python.org instructions <https://packaging.python.org/tutorials/packaging-projects/>`_::

  pip install setuptools wheel
  python setup.py sdist bdist_wheel
  python twine upload dist/*

