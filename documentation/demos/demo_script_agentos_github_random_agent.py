from pcs import Module
from pcs.output import Output
from pcs.registry import WebRegistry
from pcs.repo import Repo

# download agent Module, its dependency components, and wire them up.
repo = Repo.from_github("agentos-project", "agentos")
c_suff = "==master"
f_pref = "example_agents/random/"
ag_c = Module.from_repo(repo, f"a{c_suff}", f"{f_pref}agent.py")
env_c = Module.from_repo(repo, f"e{c_suff}", f"{f_pref}environment.py")
pol_c = Module.from_repo(repo, f"p{c_suff}", f"{f_pref}policy.py")
ds_c = Module.from_repo(repo, f"d{c_suff}", f"{f_pref}dataset.py")

env_c.instantiate = True
env_c.class_name = "Corridor"

ag_c.instantiate = True
ag_c.class_name = "BasicAgent"
ag_c.add_dependency(env_c, "environment")

pol_c.instantiate = True
pol_c.class_name = "RandomPolicy"
ag_c.add_dependency(pol_c, "policy")
pol_c.add_dependency(env_c, "environment")

ds_c.instantiate = True
ds_c.class_name = "BasicDataset"
ag_c.add_dependency(ds_c, "dataset")


# Run the agent component
r = ag_c.run_with_arg_set("run_episode", {})

# Publish the agent run to the local WebRegistry
wr = WebRegistry("http://localhost:8000/api/v1")
r.to_registry(wr)

# Now load it back in from the WebRegistry and run it.
loaded_run = Output.from_registry(wr, r.identifier)
loaded_run.run_command.run()
