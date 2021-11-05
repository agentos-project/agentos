"""Test suite for AgentOS Component."""
from agentos import Component


def test_component_repl_demo():
    class SimpleAgent:
        def __init__(self):
            env_name = self.env.__class__.__name__
            print(f"SimpleAgent: AgentOS added self.env: {env_name}")

        def reset_env(self):
            self.env.reset()

    class SimpleEnvironment:
        def reset(self):
            print("SimpleEnvironment.reset() called")

    # Generate Components from Classes
    agent_component = Component(SimpleAgent)
    environment_component = Component(SimpleEnvironment)

    # Add Dependency to SimpleAgent
    agent_component.add_dependency(environment_component, alias="env")

    # Instantiate a SimpleAgent and run reset_env() method
    agent = agent_component.get_instance()
    agent.reset_env()
