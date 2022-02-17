===============================================
Registry for Environments, Policies, and Agents
===============================================

Current Version: v7

See `Revision History`_ for additional discussion.

Abstract
========

An AgentOS agent is composed of **components**.  A component is a shareable,
swappable package that adheres to a specific API which an agent can incorporate
into itself.  Currently, components correspond to the core AgentOS abstractions
(i.e. Environments and Policies).  See the `Core Abstractions Design Doc
<https://github.com/agentos-project/design_docs/blob/main/abstractions.rst>`_
for more info.

This document proposes the **AgentOS component registry (ACR)**.  ACR allows
for easy composition and reuse of AgentOS components much like ``pip`` does for
Python and ``APT`` does for Debian Linux.

The ACR is integrated with the AgentOS command-line interface (CLI) and a
centralized registry that provides information for discovering and installing
components.  It is also a part of the AgentOS runtime which exposes installed
components within your Agent code.


Rationale
=========

A primary goal of AgentOS is to provide a clean set of abstractions that will
accelerate the research and development of agent systems.  These abstractions
provide a straightforward way to swap in existing components to create new
agents with different behaviors and learning strategies; as long as each
component respects its interface, the specifics of its implementation should
not matter for composition.

The ACR enables this vision by:

* Maintaining a centralized registry of agent components including policies and
  environments.

* Providing a versioning system for these components

* Providing a command-line interface to install these components

* Providing a module for composing components within agents


Demo
====

This section illustrates the usage of ACR by way of example commands and code.

Interaction with the registry
-----------------------------

First, ensure AgentOS is installed in your environment::

  pip install agentos

Then create a new agent::

  mkdir demo_agent
  cd demo_agent
  agentos init . -n DemoAgent

This generates a minimal agent in your ``demo_agent`` directory.  The minimal
agent is not particularly interesting though, so let's flesh it out.

Let's take a look at the environments available to our agent in the ACR::

  agentos search environment

The above command returns the listings for all components of type
``environment``.  Now, let's install the ``2048`` environment that models
the in-browser game `2048 <https://en.wikipedia.org/wiki/2048_(video_game)>`_::

  agentos install environment 2048

The above command not only installs the 2048 environment into your agent
directory, but it also updates our agent directory's ``agent.ini`` file to
record the specifics of the components we've installed. Details about the
``agent.ini`` file can be found `here
<https://github.com/agentos-project/design_docs/blob/main/abstractions.rst#agent-definition-file>`_.

Our agent will now run against the 2048 game environment.  Now, let's install a
policy that our agent can use to determine which action to take when given a
set of observations::

    agentos install policy q_table

We'll use a Q table to track the quality of the actions available to our agent
in a given state. Policies generally come with an `improve()` method which gets
called when the agent wants to update its policy based upon experience.
Policies are also often backed by state (in this case, a data structure
representing the Q table).

We can now tell our agent to learn so that it becomes better at playing 2048 as
follows::

  agentos learn -f agent.ini 1000

And we can run our agent as follows::

  agentos run -f agent.ini

As you let your agent run, you'll get periodic updates on its performance
improvement as it gains more experience playing 2048 and learns via the Q-table
algorithm.

Some agents will only learn when called via ``agentos learn`` and will have
their policy frozen during ``agentos run``.  Other agents will learn whenever
they are run via either method.  This is design decision is up to the agent
developer and the algorithm they are implementing.

Now suppose we become convinced that a `Deep Q-Learning network
<https://en.wikipedia.org/wiki/Q-learning>`_ would be more amenable to learning
2048.  Switching our policy is as easy as running::

  agentos install policy dqn

Because you are installing a second policy, ACR will ask you which you'd like
to make default.  All installed components are always programmatically
accessible as members in the agent (e.g. ``self.environments.2048``), but ACR
initializes the members ``Agent.environment`` and ``Agent.policy`` with the
default policy and environment respectively.

Go ahead and set ``dqn`` as the default policy.  Again, ``agent.ini`` will be
updated to reflect that we are now using a DQN-based learning algorithm instead
of a Q-table based learning algorithm.

Now when you tell your agent to learn again (``agentos learn``) your agent will
be using Q-learning with a deep Q network to learn 2048.


Using components within code
---------------------------

Let's dig into our minimal agent to see how we access our components
programmatically::

    from agentos import Agent

    class DemoAgent(Agent):
        def learn(self):
            self.policy.improve()

        def advance(self):
            next_action = self.policy.decide(self.obs)
            self.obs, done, reward, info  = self.environment.step(next_action)

ACR automatically loads default components into class members of the agent such
as ``self.policy`` and ``self.environment``.  If you have more than one
component installed for a particular role (e.g. two complementary environments)
then you can access each component within the agent via their name::

  self.environments.2048.step()
  ...
  self.environments.cartpole.step()


MVP
===

* ACR will be able to access a centralized registry of policies and
  environments

  * V0 target: the list will be a yaml file stored in the AgentOS repository

* Each registry entry will be structured as follows::

    component_name:
      type: [policy | environment]
      agent_os_versions:
        - [compatible with this AgentOS version]
        - [compatible with this AgentOS version]
      description: [component description]
      releases:
        - name: [version_1_name]
          hash: [version_1_hash]
          github_url: [url of version 1 repo]
          file_path: [path to py file containing class to import]
          class_name: [fully qualified class name of version 1]
          requirements_path: [path to version 1 requirements file]

        - name: [version_2_name]
          hash: [version_2_hash]
          github_url: [url of version 2 repo]
          file_path: [path to py file containing class to import]
          class_name: [fully qualified class name of version 1]
          requirements_path: [path to version 2 requirements file]

  for example::

    2048:
      type: environment
      agent_os_versions:
        - 1.0.0
        - 1.1.0
      description: "An environment that simulates the 2048 game"
      releases:
        - name: 1.0.0
          hash: aeb938f
          github_url: https://github.com/example-proj/example-repo
          file_path: environment.py
          class_name: 2048
          requirements_path: requirements.txt

        - name: 1.1.0
          hash: 3939aa1
          github_url: https://github.com/example-proj/example-repo
          file_path: environment.py
          class_name: 2048
          requirements_path: requirements.txt

* Each component will be a (v0: Python) project stored in a Github repo.

* ACR will have an ``search`` method that will list all components in the
  registry matching the search query.

* ACR will have an ``install`` method that will:

  * Find the components location based on its registry entry

  * Ask if you'd like to install the component as the default in cases where
    there are multiple installed components of the same type.

  * Clone the component's Github repo

  * Update the agent directory's ``agent.ini`` to include the component in
    its default configuration

  * Register the component locally so that it is accessible via the ``acr``
    module

  * Add a line to the agent directory's requirements file that links to the
    component's requirements file (e.g. a line of the form
    `-r component/repo/path/requirements.txt`.).

* ACR will have an ``uninstall`` method that will remove the component from the
  agent directory (including any links to the component's requirements).

* Components can be programmatically accessed from the ``acr`` module

* Developers have an easy way to register their local custom components with
  ``acr`` so it can be accessed via the ``acr`` module in other parts of their
  agent.

* The minimal agent (``agentos init``) will be ACR aware and incorporate
  basic components with minimal required edits


Long Term Plans
===============

* A simple way for component authors to submit components to the registry via
  command-line and web interface.
    * For example, this might be two commands:
        * ``agentos package ...`` - packages up the component
        * ``agentos register ...`` - pushes the component listing to the
          centralized registry

* A way for agent developers to detect and resolve requirement conflicts
  between already-installed and soon-to-be-installed components.

* Agents are not components, but it still seems like it'd be useful to share
  agents.  Long term, we will extend the registry system to encompass agents as
  well.

* Break ACR into two components:

    * Package management functionality:
        * ``agentos install``
        * ``agentos search``
        * ``agentos uninstall``
        * ``agentos status`` - new command to show what's available in your
          agent

    * Git-like mapping tools
        * commands to map particular versions of installed components to
          particular members available in the Agent class.

* Expose the state backing a particular policy as a separate, shareable
  component.


FAQ
===

**Q:** My [complex component] has a number of hyperparameters that need to be
tuned based on the particulars of the environment and the agent.  How do I do
this?

**A:** Each component exposes a configuration in its ``agent.ini`` entry. This
allows for both manual tweaking of hyperparameters as well as programmatic
exploration and tuning (with e.g. `sk-learn grid search
<https://scikit-learn.org/stable/modules/grid_search.html>`_).  See also the
example ``agent.ini`` file `here
<https://github.com/agentos-project/design_docs/blob/main/abstractions.rst#agent-definition-file>`_.


**Q:** How can I reuse a policy from a previous run?

**A:** Policies are top-level components and are often backed by some sort of
state.  ``agentos run`` has tooling that allows you to dynamically specify when
and how to reuse existing models.

**Q:** Can only 1 component of each type be installed in an agent at a time?

**A:** ACR allows multiple components of a single type. The ``agent.ini``
configuration file defines the default for each component type and that default
is accessible programmatically via shortcuts within the agent like
``self.policy`` and ``self.environment``.

In an agent where you have, for example, two policies installed (e.g.
``random`` and ``dqn``) the default (as determined by ``agent.ini``) will be
accessible within the agent as ``self.policy``, but both will always be
accessible at ``acr.policies.random`` and ``acr.policies.dqn`` respectively.

**Q:** How does AgentOS locate the main code of the component within the Github
repo? Must all components have a well known entry point (e.g., a file called
main.py)?

**A:** The ACR registry entry for each version of a component contains
sufficient information to discover the entry point of the component and its
requirements.

We may eventually:

* Require a component's repo to store additional metadata (perhaps in a
  top level ``agent.ini`` file) that ACR tooling can ingest to alleviate
  concerns about mismatches between registry info and repo info (e.g. a
  component's version is different in the registry and in the repo).

* Require all components to be proper Python packages so we can reuse Python's
  ``setup.py`` tooling.


**Q:** Will we update the code generated by ``agentos init`` so that it will
use the ACR module?

**A:** Yes, the default agent uses some very basic components that are included
out-of-the-box in AgentOS (e.g. random action policy, a basic corridor
environment).  The ``agentos init`` command creates the ``agent.ini`` file that
specifies these defaults.

**Q:** Do we want to design the API so that using a component from the registry
looks exactly (or nearly) the same as using a hand-built component.  Basically,
should we recommend using the same sort of composition for both composing an
agent from an environment, policy, and algorithm built from scratch and
composing an agent entirely from pre-built components in the registry?

**A:**  Yes, I think nudging users toward consistency would be good.  I think
that means component specifications and APIs that are well documented and
tooling that makes it valuable to build to those specs.

Ultimately, if someone wants to give their custom environment a nonstandard
``proceed_one_step_in_time()`` function instead of a ``step()`` function, we
shouldn't try to stop them.  But we should instead strive to make it high-value
to standardize because you can use a bunch of great tools out-of-the-box on
your component programmed to the spec.

Diving down closer to the code, I think we need to provide an easy way to, for
example, register your custom environment so that you can access it via
``self.environment`` within your agent, and encourage exposing and interacting
with your custom components in this way.


**Q:** How does this relate to OpenAI's ``gym.envs.registry``, if at all?

**A:** The idea of having an ``acr`` module that you can import in your Python
code is inspired by the ``gym.envs.registry``.  The ``acr`` module dynamically
loads in the available components much like gym's registry.

One rationale I found for OpenAI's environment registry is
[here](https://github.com/openai/gym/blob/master/gym/envs/registration.py#L76)
and essentially amounts to versioning an environment.  We solve this problem by
requiring a git hash for every "released" version of a component.

**Q:** How does this relate to how AgentOS uses MLflow for Agent Directories.
Should we merge the two concepts? Or at least unify them? Maybe get rid of the
dependency on MLflow?

**A:**  I think MLflow will be useful and should remain a dependency; one will
still have to perform various runs with an agent (e.g. to tune hyperparameters)
and MLflow's tracking and visualization should be useful for that.

In fact, one could think of the components themselves as hyperparameters to the
agent, and some sort of deeper integration with MLflow would probably be
valuable ("On the first run I used a Deep Q Network component with 128 nodes to
represent my Q function, while on my second run I used a table component with
512K entries").

TODO and open questions
=======================

* How to handle component dependencies (Both package and component-level)?

  * `StackOverflow on conditional requirements <https://stackoverflow.com/a/29222444>`_
  * How to fail gracefully if there are incompatible requirements
  * Perhaps use separate processes to isolate run environments
  * Can we just use the Python package system and pip directly?

* What are the key components that we want to expose in our registry?
  Candidates: Agents, Policies, Environments, Policy-state

Revision History
================

* Discussion Thread:

  * `AgentOS Component Registry <https://github.com/agentos-project/design_docs/discussions/7>`_

* Important pull requests:

  * `design_docs #1: AgentOS registry <https://github.com/agentos-project/design_docs/pull/1>`_
  * `design_docs #2: Avoid merging requirements on component install <https://github.com/agentos-project/design_docs/pull/2>`_
  * `design_docs #10: Design doc updates: Abstractions and Registry <https://github.com/agentos-project/design_docs/pull/10>`_

* Document version history:

  * `v1 <https://github.com/agentos-project/design_docs/blob/36791f4ef1cf408c19cf13042bb7cc6b72cb6030/registry.rst>`_
  * `v2 <https://github.com/agentos-project/design_docs/blob/020a70a5e538b58e5e0ff269f44a7f206a7b132e/registry.rst>`_
  * `v3 <https://github.com/agentos-project/design_docs/blob/e32ff7a96eab3486a3c8bb65c1ca1df280e20434/registry.rst>`_
  * `v4 <https://github.com/agentos-project/design_docs/blob/507bfb96a1b40bef8338603a3e661681d0d622c7/registry.rst>`_
  * `v5 <https://github.com/agentos-project/design_docs/blob/886f5a0eb960c398cc57d7cd5ec97956c528cca4/registry.rst>`_
  * `v6 <https://github.com/agentos-project/design_docs/blob/2ec8b7f231330119d153a24725537a7c4e71084d/registry.rst>`_

    * Rename AgentOS Component System (ACS) to AgentOS Component Registry (ACR)

    * Rename ``components.ini`` to ``agent.ini``

    * Update demo to reflect core abstractions and new CLI

    * Update FAQ to reflect recent discussions on core abstractions

  * `v7 <https://github.com/agentos-project/design_docs/blob/271b7450c0d1c50540f170857d9a6357acbd8fd7/registry.rst>`_

    * Address discussion feedback `here
      <https://github.com/agentos-project/design_docs/discussions/7#discussioncomment-361544>`_.

    * Address meeting feedback `here
      <https://github.com/agentos-project/design_docs/discussions/7#discussioncomment-364414>`_.

    * Rewrote abstract to better define terms

    * Removed Trainer abstraction

    * Reworked demo (no Trainer, updates to CLI interface)

    * Update registry entry spec

    * Added more long term plans

Further Reading
===============

* `AgentOS Issue 68: Registery for Envs, Policies, and Agents <https://github.com/agentos-project/agentos/issues/68>`_
* `PEP 301 -- Package Index and Metadata for Distutils <https://www.python.org/dev/peps/pep-0301/>`_
* `PEP 243 -- Module Repository Upload Mechanism <https://www.python.org/dev/peps/pep-0243/>`_
