## Stable Baselines3 PPO Agent port

This is the same as `example_agents/sb3_agent/`, but runs against versions of
components available on GitHub.

### Agent Training

Train the agent by running the following from the command-line:

```bash
agentos run agent --entry-point learn
```

Optional command-line arguments:

* `-A total_timesteps=X` - Run the learning algorithm for X environment steps.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run agent --entry-point evaluate
```

Optional command-line arguments:

* `-A n_eval_episodes=X` - Evaluate the agent over X episodes.


### Agent Reset

Reset agent (including the backing model) by running the following from the
command-line:

```bash
agentos run agent --entry-point reset
```

### Publish a run

To see runs:

```bash
agentos status
```

To publish a particular run:


```bash
agentos publish-run RUN_ID
```
