from pcs import Component
from pcs.registry import WebRegistry

random_agent = Component.from_registry_file(
    "example_agents/sb3_agent/components.yaml", "sb3_agent"
).to_versioned_component()
run = random_agent.run_with_arg_set("evaluate", {})
wr = WebRegistry("http://localhost:8000/api/v1")
run.to_registry(wr)
