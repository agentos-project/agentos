## Stable Baselines3 PPO Agent port

By default, this agent runs against environment `CartPole-v1`.  To run against
environment `PongNoFrameskip-v4`, add the following flag to the commands below:

```bash
--arg-set-file ppo_pong_args.yaml
```


### Agent Training

Train the agent by running the following from the command-line:

```bash
agentos run sb3_agent --function-name learn
```

Optional command-line arguments:

* `-A total_timesteps=X` - Run the learning algorithm for X environment steps.


### Agent Evaluation

Evaluate the agent by running the following from the command-line:

```bash
agentos run sb3_agent --function-name evaluate
```

Optional command-line arguments:

* `-A n_eval_episodes=X` - Evaluate the agent over X episodes.


### Agent Reset

Reset agent (including the backing model) by running the following from the
command-line:

```bash
agentos run sb3_agent --function-name reset
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
