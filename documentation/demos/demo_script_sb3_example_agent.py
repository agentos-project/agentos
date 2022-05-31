import requests

from pcs import Module

# from pcs.registry import WebRegistry

requests.get("http://localhost:8000/empty_database")
random_agent = Module.from_registry_file(
    "example_agents/sb3_agent/components.yaml", "sb3_agent"
).to_versioned_module()

# This first run will be start training an agent from stractch.
learning_run = random_agent.run_with_arg_set(
    "learn",
    {
        "sb3_agent": {
            "__init__": {
                "load_most_recent_run": False,
            }
        }
    },
)

# This second run will automatically load in the model trained
# by the first run and continue to improve it.
learning_run = random_agent.run_with_arg_set("learn", {})

# run = random_agent.run_with_arg_set("evaluate", {})
# wr = WebRegistry("http://localhost:8000/api/v1")

# You can publish the Output to locally running WebRegistry server
# via the following command:
# run.to_registry(wr)

# OR, update and uncomment the code below to publish the AgentOutput itself.
# Look at the output printed by the call to `run_with_arg_set()` above,
# and copy the ID of the AgentOutput from the line that looks similar to this:
# "Results for AgentOutput 85ad300d7d86461c938444063de68343"
# from agentos import AgentOutput
# agent_run_id = XXXXXXXXXXXXXXXXXXXXXXX
# from pcs.registry import WebRegistry
# sb3_agent_run = AgentOutput.from_existing_mlflow_run(agent_run_id)
# wr = WebRegistry("http://localhost:8000/api/v1")
# sb3_agent_run.to_registry(wr)
