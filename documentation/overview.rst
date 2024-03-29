***********************************
Python Component System (PCS) Intro
***********************************

The Python Component System (PCS) is an implementation of what we call the
**component programming model**. The goal of the component programming model
is to provide:

* Reproducibility
* Experiment Tracking
* Virtual Environment Management
* Composability, and
* Sharing
  
to Python programmers with minimal additional requirements and complications in
their code. The component programming model provides a **standard, reproducible
way** to setup, run, capture the outputs and results of a Python program, and
then share these outputs and results with collaborators.

Key Features
------------

The key features provided by PCS, our implementation of the component programming model, are:

* A standard reproducible way to run Python code.
* Transparent handling of dependency and environment management.
* An API to ``pip`` and ``virtualenv``.
* Support for easy, decentralized sharing of code and run history.
* Full code lifecycle handling from setup to running to capturing run results.
* All functionality available from within Python and on the command-line.
* Integrates with the existing Python ecosystem.
* Ability to incrementally adopt PCS functionality as your project requirements
  become better defined.



Key Concepts
------------

At the core of PCS is the idea of a **Module**.  A Module is an
abstraction for encapsulating and sharing runnable Python code in a way that is
portable and easy to reproduce.  A Module wraps a Python object (e.g. a
class instance, a class, or a module) and tracks that object's setup
requirements as well as its inputs and outputs.

More specifically, a Module consists of the following information:

* Repo - a reference to a location where the source code can be fetched (e.g. a
  git URL)

* Module Path - the location of a Python file within the repo from which the
  managed object can be fetched.

* Object Name - the name of the Python object the Module manages.

* Requirements Path - the location of a requirements file that can be installed
  using ``pip`` (or a ``setup.py`` file) that list the packages needed by the
  Module to run.

* Dependencies - a list of other Components on which this Module depends.

A developer uses a Module by running an **entry point** on it.  An entry
point is a managed, runnable function on the Module.  A Module may have
one or more entry points, and an entry point may be passed arguments (via a
:py:func:`pcs.argument_set.ArgumentSet`) when run.  When an entry point is run in the PCS runtime, it
automatically has its inputs and outputs instrumented and recorded for
reproducibility and sharing purposes.

When a Module's entry point is run under PCS, a **Run** object gets created.
Runs are used for tracking the outputs of executing code, which can be used for
debugging, analysis, and as the inputs by subsequent runs. Runs can be shared.

In PCS, Runs provide a logging interface and track the outputs and results of
code execution.  A **Module Run** is a specific type of Run that contains
information about about a particular execution of a Module's entry point
with a particular Argument Set.  Whenever an entry point is executed under
PCS, a Module Run gets created.

All Runs enforce semantics around the type of outputs and results they track,
dividing the world into info, data, and artifacts:

* Info is metadata (start-time, mlflow_run_id)
* Data can be metrics, parameters, and tags
* Artifacts are files or folders produced during the Run
  
PCS's Run class is a wrapper `MLflow's <https://mlflow.org>`_ Run interface and
uses both an MlflowClient and an MLflowRunID.

The reproducibility and shareability features of PCS derive from the fact that
all the concepts discussed so far (e.g. Components, Argument Sets, Runs, etc)
can be serialized out to a plain-text **Spec**.  Because all of these things
can be represented as simple specs, sharing is as easy as sending a text file
from one instance of PCS to another.

To aid in sharing, PCS also provides a **Registry** interface.  A Registry
provides a way to store and retrieve specs.  PCS includes several
implementations of Registries, including one backed by the local filesystem and
one backed by a web server.
