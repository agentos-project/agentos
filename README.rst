==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source **python API and a command line interface** for building, running, and sharing learning agents. AgentOS is licensed under the Apache License, Version 2.0.

|Tests Status|

.. |Tests Status| image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions)
  :alt: Test Status Indicator

Requires Python >= 3.5 (because the CLI uses pathlib)


Install and try it out
----------------------
Install agentos, and then run a simple agent::

  # First make sure you're using python 3.5 or newer.
  pip install agentos
  agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv

Then, create, explore, and extend your first Agent::

  mkdir my_agent
  cd my_agent
  agentos init
  agentos run

Also, check out the example agents in the `example_agents <https://github.com/agentos-project/agentos/tree/master/example_agents>`_ directory of the project source code.

Learn more and see the docs at `agentos.org <https://agentos.org>`_.


Developing (installing from source)
-----------------------------------
To install agentos from source (e.g., to play with the example_agents), run the following::

  git clone https://github.com/agentos-project/agentos.git
  pip install -e agentos # you may want to do this inside a virtualenv or conda env.


Tests
-----
To run tests::

  pip install -r test-requirements.txt
  pytest all_tests.py


Building Website
----------------
The sourece for the agentos.org is in the `website` directory.
agentos.org is a github.io website, so if you push changes to the `docs`
directory in the `website` branch, those changes will become live at 
agentos.org automatically.

To build the website you'll need to install and use `jekyll <https://jekyllrb.com/>`_:::

  gem install jekyll bundler
  cd website
  bundle exec jekyll build # or replace build with serve to run a local jekyll server


Building Documentation
----------------------

The documentation is in the `docs` direcory and written in `ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.
To build the docs you'll need to use `Sphinx <https://www.sphinx-doc.org>`_.

To build the docs locally, use::

  pip install Sphinx==3.4.1 sphinx_rtd_theme==0.5.0 # these are also included in test-requirements.txt
  sphinx-build docs docs/_build



Pushing to PyPI
---------------
To push a release to PyPI, follow `these python.org instructions <https://packaging.python.org/tutorials/packaging-projects/>`_::

  pip install setuptools wheel twine
  python setup.py sdist bdist_wheel
  python twine upload dist/*

