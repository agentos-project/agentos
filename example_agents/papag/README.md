## Ilya Kostrikov's PyTorch A2C PPO, ACKTR, and GAIL (PAPAG) Repo 

[Repo](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#atari)

### A2C

AgentOS Train:

```
agentos run papag_agent --function-name learn --registry-file components.yaml --registry-file a2c_pong_args.yaml --arg-set-id a2c_pong_args
```

AgentOS Evaluate:

```
agentos run papag_agent --function-name learn --registry-file components.yaml --registry-file a2c_pong_args.yaml --arg-set-id a2c_pong_args
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#a2c).

### PPO

train:

```
agentos run papag_agent --function-name learn --registry-file components.yaml --registry-file ppo_pong_args.yaml --arg-set-id ppo_pong_args
```

evaluate:

```
agentos run papag_agent --function-name evaluate --registry-file components.yaml --registry-file ppo_pong_args.yaml --arg-set-id ppo_pong_args
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#ppo).


### ACKTR

train:

```
agentos run papag_agent --function-name learn --registry-file components.yaml --registry-file acktr_pong_args.yaml --arg-set-id ppo_pong_args
```

evaluate:

```
agentos run papag_agent --function-name evaluate --registry-file components.yaml --registry-file acktr_pong_args.yaml
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#acktr).
