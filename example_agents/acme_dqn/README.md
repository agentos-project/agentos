## Acme DQN Agent port

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


