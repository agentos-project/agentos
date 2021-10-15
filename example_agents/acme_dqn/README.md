## Acme DQN Agent port

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


