AgentOS is a python API and a command line interface for building, running, and sharing learning agents.

Requirements: Python >= 3.5 (because of pylib dependency)

To install:

```
git clone git@github.com:andyk/agentos.git
pip install -e agentos
```


To create and play with your first Agent:

```
mkdir my_agent
cd my_agent
agentos init
# Edit agentos dependency in ./conda_env.yaml
# Only necessary until we are in PyPI.
agentos run
```

See design doc, documentation, draft draft white paper at https://docs.google.com/document/d/13PoOxTs2bNPpEhVN5uHHlA0BKrIIHNc5iK8zhDvIrLc/edit
