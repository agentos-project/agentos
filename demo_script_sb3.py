from agentos.argument_set import ArgumentSet
from agentos.component import Component
from agentos.component_run import ComponentRun
from agentos.registry import Registry, WebRegistry
from agentos.repo import Repo

# sb3_repo = Repo.from_github("DLR-RM", "stable-baselines3")
# sb3_reg = Registry.from_repo(sb3_repo)
sb3_reg = Registry.from_yaml("/tmp/sb3_registry_inferred.yaml")

sb3_comp = Component.from_registry(
    sb3_reg, "module:stable_baselines3____init__.py"
)
sb3_comp.class_name = "PPO"
sb3_comp.instantiate = True
arg_set = ArgumentSet(
    {
        "module:stable_baselines3____init__.py": {
            "__init__": {"policy": "MlpPolicy", "env": "CartPole-v1"},
            "learn": {"total_timesteps": 10000},
        }
    }
)
run = sb3_comp.run_with_arg_set("learn", arg_set, log_return_value=False)

# Write a run to your local WebRegistry, then read it back in.
wr = WebRegistry("http://localhost:8000/api/v1")
run.to_registry(wr)
run_from_web_reg = ComponentRun.from_registry(wr, run.identifier)

# Try creating a new run from the run_command loaded in from the WebRegistry
new_run = run.run_command.run()

# Write the new run to a file, read it back in, and run it.
new_run.to_registry().to_yaml("/tmp/run_sb3.yaml")
loaded_run_reg = Registry.from_yaml("/tmp/run_sb3.yaml")
loaded_run = ComponentRun.from_registry(loaded_run_reg, new_run.identifier)
loaded_run.run_command.run()

# Make sure we can write a run that was read in from a file registry
# out to a WebRegistry.
# loaded_run.to_registry(wr)
# ComponentRun.from_registry(wr, loaded_run.identifier)
