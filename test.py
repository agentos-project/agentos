from agentos.component import Component
from agentos.parameter_set import ParameterSet


url = (
    "https://github.com/agentos-project/agentos/"
    "blob/master/example_agents/sb3_agent/components.yaml"
)
component_name = "sb3_agent"

component = Component.from_github_registry(url, component_name, use_venv=True)
component.run("evaluate", ParameterSet({}))
