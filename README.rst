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

AgentOS requires Python 3.5 - 3.8 and `conda`. To get started, use pip to
install agentos, and then run a simple agent::

  # Make sure you're using Python 3.5 - 3.8
  # Make sure you have miniforge, miniconda, or conda installed (required
  # for `agentos run`, which uses MLflow Projects).
  pip install agentos
  agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv

Then, create and run your first Agent::

  mkdir my_agent
  cd my_agent
  agentos init
  agentos run

This type of agent is called an `Agent Directory <../agent_directories>`. To
see more complex agents, look at example agents in the `example_agents
<https://github.com/agentos-project/agentos/tree/master/example_agents>`_
directory of the project source code.


Development Process
===================

AgentOS uses `GitHub Issues
<https://github.com/agentos-project/agentos/issues>`_ to track development
work.  Submit any bug reports or feature requests to this issues tracker.

For significant feature work (more than a couple dev days or something that
fundamentally changes internal or external interfaces), we run a design process
to solicit feedback from other collaborators.  Read more about this process
in the `Proposing Features`_ section.

To contribute to AgentOS, the general workflow is as follows:

* Sync with the core development team via the
  `issue tracker <https://github.com/agentos-project/agentos/issues>`_
  so we can avoid unnecessary or duplicated work.

* Fork the AgentOS repo.

* Complete your feature work on a branch in your forked repo.  Ensure all
  checks and tests pass.

* Issue a pull request from your forked repo into the central AgentOS repo.
  Assign a core developer to review.

* Address any comments and the core developer will merge once the PR looks
  good.


Proposing Features
==================

For new features and other big chunks of work, AgentOS uses a design process
centered around design proposals, discussions, and design docs. The goal of the
process is to:

* Allow developers to think through a design, and
* Allow stakeholders to give feedback

...before development begins.

If you'd like to propose a feature, please follow the procedure found in the
`design_docs README <documentation/design_docs/README.rst>`_.  You can also
browse existing design docs in the folder to get a feel for the general
content and style.


Installing AgentOS From Source
==============================

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


Building Docs
=============

The documentation source is in the ``documentation`` directory and written in
`ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.  The docs are
built using `Sphinx <https://www.sphinx-doc.org>`_.  To build the docs, first
install the dev requirements::

  pip install -r dev-requirements.txt

Then use the build script::

  python scripts/build_docs.py

Use the ``--help`` flag to learn more about other optional flags that
``build_docs.py`` takes, including ``--release`` (for publishing the docs) and
``--watch`` (for auto-recompiling the docs whenever doc source files are
changed).

Notice that the build file puts the compiled docs into ``docs/<version_num>``
where ``version_num`` comes from ``agentos/version.py``.

Or you can build the docs manually (e.g., to control where output goes)::

  sphinx-build documentation outdir  # Or use sphinx-autobuild.
  # Open and inspect outdir/index.html in your browser.


Publishing Docs to agentos.org
==============================

`agentos.org <https://agentos.org>`_ is a github.io website where the AgentOS
docs are hosted.  To publish updated docs to agentos.org, checkout the
``website`` branch and build the docs per the instructions above, then create a
PR against the ``agentos-dev/website`` branch. Once committed, those changes
will become live at agentos.org automatically.

Assuming you have local branches tracking both the ``master`` and ``website``
branches, and all changes to the documentation source files have all been
committed in the ``master`` branch, the workflow to publish updated docs to
agentos.org might look similar to::

  git checkout website
  git merge master
  python scripts/build_docs.py --release -a  # The -a is a `sphinx-build` flag.
  git add docs
  git commit -m "push updated docs to website for version X.Y.Z"
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

#. Build and check the distribution artifacts for the release by running::

   pip install -r dev-requirements.txt
   python setup.py sdist --formats=gztar,zip bdist_wheel
   twine check dist/*

   This will create a `wheel file <https://wheel.readthedocs.io/en/stable/>`_
   as well as tar.gz and zip source distribution files, and catch any blockers
   that PyPI would raise at upload time. Fix any errors before proceeding.

#. Create a release pull request (PR) that:

   * Removes "-alpha" suffix from the version number in ``agentos/version.py``.
   * Contains draft release notes (summary of major changes).

#. Wait till the PR gets LGTMs from all other committers, then merge it.

#. Build and publish the docs for the new version, which involves creating a
   pull request against ``website`` branch. This is required for all releases,
   even if the docs have not changed, since the docs are versioned. When you
   run the ``build_docs.py`` script, you will use the ``--release`` flag
   (see `Building Docs`_ & `Publishing Docs to agentos.org`_ for more details).

#. Create another follow-on PR that bumps version number to be ``X.Y.Z-alpha``
   which reflects that work going forward will be part of the next release
   (we use `semantic versioning <https://semver.org>`_).

#. Push the release to PyPI (see `Pushing Releases to PyPI`_).

#. Create a `github release
   <https://github.com/agentos-project/agentos/releases>`_ and upload the
   tar.gz and zip source code distribution files. This will create a git tag.
   For the tag name, use "vX.Y.Z" (e.g. v0.1.0).


Pushing Releases to PyPI
========================

We make AgentOS `available in PyPI <https://pypi.org/project/agentos/>`_. To
push a release to PyPI, you can approximately follow `these python.org
instructions <https://packaging.python.org/tutorials/packaging-projects/>`_,
which will probably look something like::

  pip install -r dev-requirements.txt
  rm -rf dist
  python setup.py sdist --formats=gztar bdist_wheel
  twine check dist/*
  twine upload dist/*


----

*This README was compiled from the project documentation via:*
``python documentation/build_readme.py``.