from pcs import ArgumentSet, Component

# from pcs.registry import WebRegistry

papag_agent = Component.from_registry_file(
    "example_agents/papag/components.yaml", "agent"
).to_versioned_component()

a2c_pong_arg_set = ArgumentSet.from_yaml(
    "./example_agents/papag/a2c_pong_args.yaml"
)
# This first run will be start training an agent from stratch.
learning_run = papag_agent.run_with_arg_set("learn", a2c_pong_arg_set)

# This second run will automatically load in the model trained
# by the first run and continue to improve it.
learning_run = papag_agent.run_with_arg_set("learn", a2c_pong_arg_set)
