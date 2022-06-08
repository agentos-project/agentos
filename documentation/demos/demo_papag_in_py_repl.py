from pcs import ArgumentSet, Instance, Registry

reg = Registry.from_yaml("example_agents/papag/components.yaml")
reg.update(Registry.from_yaml("example_agents/papag/a2c_pong_args.yaml"))
papag_agent = Instance.from_registry(reg, "a2c_pong_papag_agent").freeze()

a2c_pong_arg_set = ArgumentSet.from_registry(reg, "a2c_pong_learn_args")

# This first run will be start training an agent from stratch.
learning_run = papag_agent.run_with_arg_set("learn", a2c_pong_arg_set)

# This second run will automatically load in the model trained
# by the first run and continue to improve it.
learning_run = papag_agent.run_with_arg_set("learn", a2c_pong_arg_set)
