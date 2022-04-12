from pcs import Component
from pcs.registry import WebRegistry

random_agent = Component.from_registry_file(
    "example_agents/sb3_agent/components.yaml", "sb3_agent"
).to_versioned_component()
run = random_agent.run_with_arg_set("evaluate", {})
wr = WebRegistry("http://localhost:8000/api/v1")

# You can publish the ComponentRun to locally running WebRegistry server
# via the following command:
# run.to_registry(wr)

# OR, update and uncomment the code below to publish the AgentRun itself.
# Look at the output printed by the call to `run_with_arg_set()` above,
# and copy the ID of the AgentRun from the line that looks similar to this:
# "Results for AgentRun 85ad300d7d86461c938444063de68343"
# from agentos import AgentRun
# agent_run_id = XXXXXXXXXXXXXXXXXXXXXXX
# from pcs.registry import WebRegistry
# sb3_agent_run = AgentRun.from_existing_run_id(agent_run_id)
# wr = WebRegistry("http://localhost:8000/api/v1")
# sb3_agent_run.to_registry(wr)
