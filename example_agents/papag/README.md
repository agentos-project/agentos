## Ilya Kostrikov's PyTorch A2C PPO, ACKTR, and GAIL (PAPAG) Repo 

[Repo](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#atari)

### A2C

AgentOS Train:

```
agentos run papag_agent --registry-file components.yaml --registry-file a2c_cartpole_args.yaml --arg-set-id a2c_cartpole_args --function-name learn
```

AgentOS Evaluate:

```
agentos run papag_agent --registry-file components.yaml --registry-file a2c_cartpole_args.yaml --arg-set-id a2c_cartpole_args --function-name learn
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#a2c).

### PPO

train:

```
TODO: once spec v2 is finished
```

evaluate:

```
TODO: once spec v2 is finished
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#ppo).


### ACKTR

train:

```
TODO: once spec v2 is finished
```

evaluate:

```
TODO: once spec v2 is finished
```

Equivalent to [this command](https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail#acktr).
