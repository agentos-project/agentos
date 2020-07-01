AgentOS is a python API and a command line interface for building, running, and sharing learning agents.

[![Tests Status - master](https://github.com/agentos-project/agentos/workflows/Python%20package/badge.svg)](https://github.com/agentos-project/agentos/actions)

Requires Python >= 3.5 (because we use pathlib)

To install:

```
git clone git@github.com:agentos-project/agentos.git
pip install -e agentos # you may want to do this inside a virtualenv or conda env.
```

Then run a simple agent that comes with AgentOS:

```
cd agentos
agentos run agentos.agents.RandomAgent gym.envs.classic_control.CartPoleEnv
```

Then, maybe create your first Agent:

```
mkdir my_agent
cd my_agent
agentos init
# Edit ./conda_env.yaml so that `agentos` dependency points to your install of agentos
# Only necessary until we are in PyPI.
agentos run
```

See design doc, documentation, draft draft white paper at https://docs.google.com/document/d/13PoOxTs2bNPpEhVN5uHHlA0BKrIIHNc5iK8zhDvIrLc/edit
