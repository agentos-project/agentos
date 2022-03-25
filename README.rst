=======================================
The Python Component System and AgentOS
=======================================

This project consists of two major pieces: the Python Component System (PCS)
and AgentOS.

Python Component System (PCS)
==================================

PCS is an open source **Python API, command line interface, and public web
registry** for building, running, and sharing Python programs.  The goals of
PCS are to:

* Make Python program execution reproducible.

* Transparently manage Python virtual environments while providing a Python API
  for ``pip`` and ``virtualenv``.

* Simplify experiment tracking and code sharing.

PCS does this by allowing you to explicitly specify dependencies and arguments
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


Quickstart
===========

See the agentos.org `quickstarts <https://agentos.org/latest/quickstart>`_.




Documentation
=============

For detailed documentation see the `agentos.org docs <https://agentos.org/latest>`_.


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

To run tests, first install the requirements (note, this script installs the
Python requirements into the currently active virtual environment)::

  cd agentos # the project root, not the nested agentos/agentos dir
  python install_requirements.py

Then run the tests::

  pytest

Also, we use Github Actions to run tests with every commit
and pull request (see the `test workflow
<https://github.com/agentos-project/agentos/blob/master/.github/workflows/run-tests.yml>`_)

If you want to the CLI to interact with a local development server, define the
environment variable (or create a `.env` file) `USE_LOCAL_SERVER=True`.

To run website tests::

  python install_requirements.py
  cd web # the web directory contained in project root
  python manage.py test

Note that some tests (e.g., see ``web/registry/tests/test_integration.py``)
test functionality for interacting with github repositories by fetching code
from https://github.com/agentos-project/agentos. Where possible, in order to
make it easy to have those tests run against code in a github repo that you can
change during development without disrupting other PRs, the test code uses
global variables defined in ``tests/utils.py`` to decide which github
repo to use when testing.

If you make changes to code that is fetched from github for use by tests, then
please follow this process for your PR:

1. While doing development, change the ``TESTING_GITHUB_REPO_URL`` and/or
   ``TESTING_BRANCH_NAME`` global variables in ``tests/utils.py``
   to point to a version of your PR branch that you've pushed to
   github. We recommend commenting out the default "prod" values of these
   variables so that you can uncomment them in the next step when the PR
   is approved for merge.
2. After your PR is approved and right before it is merged, push the branch
   you used during testing to the ``test_prod`` branch of the agentos-project
   account ``https://github.com/agentos-project/agentos.git``. And then update
   the variables in ``tests/utils.py`` (you should be able to just uncomment
   the lines you commented out in step 1 above, and delete the lines you added).


Building Docs
=============

The documentation source is in the ``documentation`` directory and written in
`ReStructuredText <https://docutils.sourceforge.io/rst.html>`_.  The docs are
built using `Sphinx <https://www.sphinx-doc.org>`_.  To build the docs, first
install the dev requirements (note, this script will install requirements into
the currently active Python virtual environment)::

  python install_requirements.py

Then use the build script::

  python scripts/build_docs.py

Use the ``--help`` flag to learn more about other optional flags that
``build_docs.py`` takes, including ``--release`` (for publishing the docs) and
``--watch`` (for auto-recompiling the docs whenever doc source files are
changed).

Notice that the build file puts the compiled docs into ``docs/<version_num>``
where ``version_num`` comes from ``pcs/version.py``.

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

    python install_requirements.py
    python setup.py sdist --formats=gztar,zip bdist_wheel
    twine check dist/*

   This will create a `wheel file <https://wheel.readthedocs.io/en/stable/>`_
   as well as tar.gz and zip source distribution files, and catch any blockers
   that PyPI would raise at upload time. Fix any errors before proceeding.

#. Create a release pull request (PR) that:

   * Removes "-alpha" suffix from the version number in ``pcs/version.py``.
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

  python install_requirements.py
  rm -rf dist
  python setup.py sdist --formats=gztar bdist_wheel
  twine check dist/*
  twine upload dist/*


----

*This README was compiled from the project documentation via:*
``python scripts/build_readme.py``.