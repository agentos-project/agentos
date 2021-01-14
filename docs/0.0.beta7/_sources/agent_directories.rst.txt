Agent Directories
=================

It is natural to expect agents to become complex and have sophisticated build systems, elaborate documentation, and many diverse dependencies.

For more than simple learning examples such as many of those contained in the ``example_agent`` source directory, we recommend using **agent directories**. An agent directory contains everything about an agent. 

To try out the agent directory approach to creating a new agent, just create a new directory and run ``agentos init`` inside it.


Dependency Management
---------------------

Much like agent composition itself, ad hoc management of an agent’s dependencies can become cumbersome, so AgentOS integrates the use of conda for dependency tracking and MLflow for reproducibly running an agent and automatically generating and re-using (when possible) conda environments.

Specifically, the ``agentos init`` command creates ``conda_env.yaml`` and ``MLProject`` files that can be edited during agent development as necessary. The ``MLProject`` file is used when the agent directory is run via the CLI command ``agentos run`` (or you can call ``mlflow run`` directly). Learn more about MLflow projects `here <https://mlflow.org/docs/latest/projects.html>`_.

Another, and perhaps more important, advantage MLflow provides over pure conda is the smart automatic creation and re-use of conda environments for a given conda environment file. A secondary advantage is allowing an agent directory to be easily shared and run by another person since MLflow projects provide this functionality.


Multiple Agent Directories
---------------------------------------

You can have as many agent directories as you want, one per agent. Each one is independent from others.

The ``agentos`` CLI is modeled after the ``git`` and ``mlflow`` CLIs, so it can’t list or manipulate all of the agents that exist on a machine (the way, e.g., that conda can with conda envs). It will undoubtedly become useful to be able to list/organize all running agents. In the future we could provide a pluggable AgentOS server or agent-store service that could, e.g., centralize the agent meta-data. Eventually we could even provide a hosted service for centrally managing agents akin to github.

