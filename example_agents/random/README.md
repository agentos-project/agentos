## Random Agent

This agent is intended for testing purposes.  It randomly walks down a 1D
corridor, has no backing data, and only dependencies on the Python standard
library.

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
