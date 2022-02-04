## Random Agent

This agent is intended for testing purposes.  It is the default agent generated
by `agentos init`. This agent randomly walks down a 1D corridor, has no backing
data, and only dependencies on the Python standard library.

### Regenerate This Agent

To regenerate this agent and update it to the latest default agent, run the
following in the agent directory:

```bash
rm -rf *.py *.yaml __pycache__ *.txt mlruns/
agentos init .
```

### Agent Training

Note this agent does not actually learn anything from training (i.e. its policy
is always random). Train the agent by running the following from the
command-line:

```bash
agentos run agent --entry-point learn
```

Optional command-line arguments:

* `-P num_episodes=X` - Run the learning algorithm for X episodes.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run agent --entry-point evaluate
```

Optional command-line arguments:

* `-P num_episodes=X` - Evaluate the agent over X episodes.
