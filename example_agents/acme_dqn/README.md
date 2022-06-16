## Acme DQN Agent port

### Agent Training

Train the agent by running the following from the command-line:

```bash
agentos run agent --function-name learn --registry-file components.yaml --arg-set-id learn_args
```

Optional command-line arguments:

* `-A num_episodes=X` - Run the learning algorithm for X episodes.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run agent --function-name evaluate --registry-file components.yaml --arg-set-id evaluate_args
```

Optional command-line arguments:

* `--arg-set-kwargs "{'num_episodes': 1}"` - Evaluate the agent over X episodes.
