==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source **python API and a command line interface** for
building, running, and sharing learning agents. AgentOS is licensed under the
Apache License, Version 2.0.

Key features include:
  * Easy to use Agent API for developing and running new agents.

  * Example learning agents from different disciplines and research areas are
    available in the
    `example_agents
    <https://github.com/agentos-project/agentos/tree/master/example_agents>`_
    directory of the project source code.

  * Reuse of OpenAI's Gym Environment abstraction.

.. image:: https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg
  :target: https://github.com/agentos-project/agentos/actions)
  :alt: Test Status Indicator

AgentOS is beta software, APIs and overall architecture are likely to change
significantly over time.


The AgentOS docs are at `agentos.org <https://agentos.org>`_.


Install and Explore
===================
AgentOS requires Python >= 3.5. To get started, use pip to install agentos, and
then run a simple agent::

  # First make sure you're using python 3.5 or newer.
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


Installing From Source
======================
To install agentos from source (e.g., to play with the example_agents), run the
following::

  git clone https://github.com/agentos-project/agentos.git
  pip install -e agentos # you may want to do this in a virtualenv or conda env.


Testing
=======
To run tests::

  cd agentos # the project root, not the nested agentos/agentos dir
  pip install -r dev-requirements.txt
  pytest test_all.py

Also, we use Github Actions to run ``test_all.py`` with every commit and pull
request (see the `test workflow
<https://github.com/agentos-project/agentos/blob/master/.github/workflows/run-tests.yml>`_)


Building Docs & agentos.org
===========================
The documentation source is in the ``documentation`` directory and written in
`ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.
The docs are built using `Sphinx <https://www.sphinx-doc.org>`_::

  python documentation/build_docs.py

Or to build the docs manually yourself::

  pip install -r dev-requirements.txt
  sphinx-build documentation docs_build  # also try installing/using sphinx-auto
  # Open and inspect docs_build/index.html in your browser.

`agentos.org <https://agentos.org>`_ is a github.io website where the AgentOS
docs are hosted.  To publish updated docs to agentos.org, build the docs and
put the output into the ``docs`` directory and the
``docs/<current_version>`` directories in the ``website`` branch. Those
changes will become live at agentos.org automatically.

Assuming you have local branches tracking both the ``master`` and ``website``
branches, and all changes to the documentation source files have all been
committed in the ``master`` branch, your workflow might look similar to::

  git checkout website
  git merge master
  python documentation/build_docs.py
  git add docs
  git commit -m "push updated docs to website"
  git push


Building README.rst
===================
The main project ``README.rst`` is built via the script
``python documentation/build_readme.py``, which re-uses sections of
documentation. This avoids duplication of efforts and lowers the chances
that a developer will forget to update one or the either of the README or
the docs.

To update ``README.rst``, first familiarize yourself with its build script
``documentation/build_readme.py``. There you can see which sections of
documentation are included in ``README.rst``, plus some text that is manually
inserted directly into ``README.rst`` (e.g., the footer).


Pushing releases to PyPI
========================
We make AgentOS `available in PyPI <https://pypi.org/project/agentos/>`_. To
push a release to PyPI, you can approximately follow `these python.org
instructions <https://packaging.python.org/tutorials/packaging-projects/>`_,
which will probably look something like::

  pip install setuptools wheel twine
  python setup.py sdist bdist_wheel
  twine upload dist/*


----

*This README was compiled from the project documentation via:*
``python documentation/build_readme.py``.