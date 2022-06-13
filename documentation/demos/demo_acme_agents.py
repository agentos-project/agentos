import pcs

reg = pcs.Registry.from_yaml("example_agents/acme_dqn/components.yaml")
agent = pcs.Component.from_registry(reg, "agent")
agent.run_evaluate()

r2d2_reg = pcs.Registry.from_yaml("example_agents/acme_r2d2/components.yaml")
r2d2_agent = pcs.Component.from_registry(r2d2_reg, "agent")
r2d2_agent.run_evaluate()
