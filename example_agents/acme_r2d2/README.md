## Acme R2D2 Agent port

This agent was broken up into finer grained components to explore communication
patterns used within Acme and to demonstrate the flexibility of the AgentOS
runtime.

### Agent Training

Train the agent by running the following from the command-line:

```bash
agentos run agent --entry-point learn --arg-set-file arguments.yaml
```

Optional command-line arguments:

* `-A num_episodes=X` - Run the learning algorithm for X episodes.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run agent --entry-point evaluate --arg-set-file arguments.yaml
```

Optional command-line arguments:

* `-A num_episodes=X` - Evaluate the agent over X episodes.


### Agent Reset

Reset agent (including the backing model) by running the following from the
command-line:

```bash
agentos run agent --entry-point reset --arg-set-file arguments.yaml
```

### Troubleshooting

If you see an error that looks like the following:

```bash
  File "/home/user/agentos/3.6env/lib/python3.6/site-packages/reverb/pybind.py", line 1, in <module>
    import tensorflow as _tf; from .libpybind import *; del _tf
ImportError: libpython3.6m.so.1.0: cannot open shared object file: No such file or directory

```

You must install the dev packages for the version of Python you are running.
For example, run the following if you are on Ubuntu running Python 3.6:

```bash
sudo apt-get install python3.6-dev
```

You may also need to reinstall Reverb and Tensorflow

```bash
pip uninstall dm-reverb tensorflow
pip install dm-reverb[tensorflow]

