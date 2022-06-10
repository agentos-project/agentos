import pcs

reg = pcs.Registry.from_yaml("example_agents/acme_dqn/components.yaml")
agent = pcs.Component.from_registry(reg, 'agent')
agent.run_evaluate()
