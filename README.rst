==================================
AgentOS: a learning agent platform
==================================

AgentOS is an open source **Python API and a command line interface** for
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
  :target: https://github.com/agentos-project/agentos/actions
  :alt: Test Status Indicator

AgentOS is beta software, APIs and overall architecture are likely to change
significantly over time.


The AgentOS docs are at `agentos.org <https://agentos.org>`_.


Install and Explore
===================

AgentOS requires Python 3.5 - 3.8. To get started, use pip to install agentos,
and then run a simple agent::

  # First make sure you're using Python 3.5 - 3.8
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
`ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.  The docs are
built using `Sphinx <https://www.sphinx-doc.org>`_.  To build the docs, first
install the dev requirements::

  pip install -r dev-requirements.txt

Then use the build script::

  python scripts/build_docs.py

Or to build the docs manually yourself (e.g., to control where output goes)::

  sphinx-build documentation docs/_build # also try installing/using sphinx-auto
  # Open and inspect docs/_build/index.html in your browser.

Notice that the build file puts the compiled docs into ``docs/<version_num>``
where ``version_num`` comes from ``agentos/version.py``.

`agentos.org <https://agentos.org>`_ is a github.io website where the AgentOS
docs are hosted.  To publish updated docs to agentos.org, checkout the
``website`` branch and build the docs per the instructions above, then create a
PR against the ``agentos-dev/website`` branch. Once committed, those changes
will become live at agentos.org automatically.

Assuming you have local branches tracking both the ``master`` and ``website``
branches, and all changes to the documentation source files have all been
committed in the ``master`` branch, your workflow might look similar to::

  git checkout website
  git merge master
  python scripts/build_docs.py
  git add docs
  git commit -m "push updated docs to website"
  git push


Building README.rst
===================
The main project ``README.rst`` is built via the script
``python scripts/build_readme.py``, which re-uses sections of
documentation. This avoids duplication of efforts and lowers the chances
that a developer will forget to update one or the either of the README or
the docs.

To update ``README.rst``, first familiarize yourself with its build script
``scripts/build_readme.py``. There you can see which sections of
documentation are included in ``README.rst``, plus some text that is manually
inserted directly into ``README.rst`` (e.g., the footer).


Releasing
=========
Here are the steps for releasing AgentOS:

#. Create a release pull request (PR) that:

   * Removes "-alpha" suffix from the version number in ``agentos/version.py``.
   * Contains draft release notes (summary of major changes).

#. Wait till the PR gets LGTMs from all other committers, then merge it.

#. Create a follow-on PR against ``website`` branch to update the docs (see
   `Building Docs & agentos.org`_), which at very least need to reflect
   the version number of the release.

#. Create another follow-on PR that bumps version number to be ``X.Y.Z-alpha``
   which reflects that work going forward will be part of the next release
   (we use `semantic versioning <https://semver.org>`_).

#. Push the release to PyPI (see `Pushing Releases to PyPI`_).

#. Create a `github release
   <https://github.com/agentos-project/agentos/releases>`_ that includes zips
   and tarzips of `wheel files <https://wheel.readthedocs.io/en/stable/>`_
   and source code (which you can generate using ``python setup.py sdist
   --formats=gztar,zip bdist_wheel`` and then manually upload to the release).



Pushing Releases to PyPI
========================
We make AgentOS `available in PyPI <https://pypi.org/project/agentos/>`_. To
push a release to PyPI, you can approximately follow `these python.org
instructions <https://packaging.python.org/tutorials/packaging-projects/>`_,
which will probably look something like::

  pip install setuptools wheel twine
  python setup.py sdist --formats=gztar,zip bdist_wheel
  twine upload dist/*


----

*This README was compiled from the project documentation via:*
``python documentation/build_readme.py``.