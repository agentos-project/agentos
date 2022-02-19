***********************************
Local Development Quick Start
***********************************

The Python Component System (PCS) can be used both on-the-fly in the Python
REPL (see :doc:`repl_quickstart`) and within a project you're developing
in your local dev environment.

In this quickstart, we'll work through an example of using PCS in a local
project.  We'll start by installing ``agentos``, run the following in your
shell::

    pip install agentos

Now, let's create a new directory for our project and initialize it.  Run the following in your shell::

    mkdir quickstart
    cd quickstart
    agentos init .

The ``agentos init .`` command creates (in the current directory) a default
project that illustrates the usage of PCS in a local development context.  You
will notice that your directory now contains a ``components.yaml`` file along
with a number of Python files.

If you inspect ``components.yaml``, you will see a human-readable manifest of
the different Python classes (found in the newly created Python files) that
this project uses.  These classes are referred to as **Components** in PCS and
they provide the foundation of any project built to execute in the PCS runtime.

The default project creates a learning agent that attempts to walk down a
1-dimensional corridor by randomly choosing to step left or right.  Let's try
to run our default project::

    agentos run agent

This command runs the default entry point of the ``agent`` Component as defined
in ``components.yaml``.  You should see output reporting how many steps your
agent took over a number of different episodes.
