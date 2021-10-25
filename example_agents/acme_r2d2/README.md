## Acme R2D2 Agent port

This agent was broken up into finer grained components to explore communication
patterns used within Acme and to demonstrate the flexibility of the AgentOS
runtime.

### Agent Training

Train the agent by running the following from the command-line:

```bash
agentos run agent --entry-point learn --param-file parameters.yaml
```

Optional command-line arguments:

* `-Pnum_episodes=X` - Run the learning algorithm for X episodes.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run agent --entry-point evaluate --param-file parameters.yaml
```

Optional command-line arguments:

* `-Pnum_episodes=X` - Evaluate the agent over X episodes.


### Agent Reset

Reset agent (including the backing model) by running the following from the
command-line:

```bash
agentos run agent --entry-point reset --param-file parameters.yaml
```


