==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source **python API and a command line interface** for building, running, and sharing learning agents. AgentOS is licensed under the Apache License, Version 2.0.

.. image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions)
  :alt: Test Status Indicator



Install and try it out
----------------------
AgentOS requires Python >= 3.5. To get started, install agentos, and then run a simple agent::

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

  $ cd agentos # the github repo root, not the nested agentos/agentos dir
  $ pip install -e .
  $ pip install -r test-requirements.txt
  $ pytest test_all.py


Building Documentation / Agentos.org Website
--------------------------------------------

The documentation is in the ``docs`` directory and written in
`ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.
To build the docs you'll need to use
`Sphinx <https://www.sphinx-doc.org>`_:::

  pip install -r documentation/requirements.txt
  ./documentation/scripts/build-docs
  # Open and inspect docs/_build/index.html in your broswer.

`agentos.org <https://agentos.org>`_ is a github.io website where the AgentOS
docs are hosted.  To publish updated docs to agentos.org, build the docs and
put the output into the ``docs`` directory and the ``docs/<current_version>``
directories in the ``website`` branch. Those changes will become live at
agentos.org automatically.

Assuming you have local branches tracking both the ``master`` and ``website``
branches, and all changes to the documentation source files have all been
committed in the ``master`` branch, your workflow might look similar to::

  pip install -r documentation/requirements.txt
  git checkout website
  git merge master
  sphinx-build documentation docs
  git add docs
  git commit -m "push updated docs to website"
  git push


Pushing to PyPI
---------------
AgentOS is `available in PyPI <https://pypi.org/project/agentos/>`_. To push a release to PyPI, follow `these python.org instructions <https://packaging.python.org/tutorials/packaging-projects/>`_::

  pip install setuptools wheel twine
  python setup.py sdist bdist_wheel
  twine upload dist/*

