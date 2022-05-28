## Ilya Kostrikov's PyTorch A2C PPO, ACKTR, and GAIL (PAPAG) Repo 

[Repo](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#atari)

### A2C

AgentOS Train:

```
agentos run papag_agent --entry-point learn --arg-set-file a2c_pong_args.yaml
```

AgentOS Evaluate:

```
agentos run papag_agent --entry-point evaluate --arg-set-file a2c_pong_args.yaml
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#a2c).

### PPO

train:

```
agentos run papag_agent --entry-point learn --arg-set-file ppo_pong_args.yaml
```

evaluate:

```
agentos run papag_agent --entry-point evaluate --arg-set-file ppo_pong_args.yaml
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#ppo).


### ACKTR

train:

```
agentos run papag_agent --entry-point learn --arg-set-file acktr_pong_args.yaml
```

evaluate:

```
agentos run papag_agent --entry-point evaluate --arg-set-file acktr_pong_args.yaml
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#acktr).

