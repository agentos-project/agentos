# Ray RLlib AgentOS Agent

This directory is a functional AgentOS agent.

That means it is also an MLflow Project.

If you are going to do any developing on this Agent, I recommend you create a conda
env to use for dev -- and update it whenever necessary -- per the following instructions:
* Start by creating a conda env using the conda_env.yaml file via something like:
  `conda env create --file conda_env.yaml`
* Then, whenever you need to add or change dependencies, don't use pip or
  other tools directly inside your env. Instead, update conda_env.yaml, and
  then run: `conda env update --file conda_env.yaml --prune`