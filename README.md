AgentOS is an open source python API and a command line interface for building, running, and sharing learning agents. AgentOS is licensed under the Apache License, Version 2.0.

[![Tests Status - master](https://github.com/agentos-project/agentos/workflows/Tests%20on%20master/badge.svg)](https://github.com/agentos-project/agentos/actions)

Requires Python >= 3.5 (because the CLI uses pathlib)


# Install and try it out
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

Also, check out the example agents in the `example_agents` directory.

Learn more and see the docs at [agentos.org](https://agentos.org).


# Tests
To run tests:

```
pip install -r test-requirements.txt
pytest all_tests.py
```


# Documentation
To build the docs you'll need to install [jekyll](https://jekyllrb.com/).

```
$ gem install jekyll bundler
$ cd docs
$ bundle exec jekyll serve
