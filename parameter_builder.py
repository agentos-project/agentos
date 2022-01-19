import pprint
from unittest.mock import MagicMock


class ParameterSet:
    def __init__(self):
        self.builder = MagicMock()

    def to_spec(self):
        spec_dict = {}
        for builder_call in self.builder.method_calls:
            component_name = None
            method_name = None
            method_name, args, kwargs = builder_call
            split_method_name = method_name.split(".")
            if len(split_method_name) == 1:
                component_name = split_method_name[0]
                method_name = "__init__"
            elif len(split_method_name) == 2:
                component_name = split_method_name[0]
                method_name = split_method_name[1]
            else:
                Exception(f"Bad builder call: {builder_call}")
            if component_name not in spec_dict:
                spec_dict[component_name] = {}

            component_dict = spec_dict[component_name]
            if method_name not in component_dict:
                component_dict[method_name] = {}
            method_dict = component_dict[method_name]
            method_dict.update(kwargs)
        return spec_dict


# Demo ParameterSet builder
parameters = ParameterSet()
parameters.builder.agent.evaluate(num_episodes=50)
parameters.builder.agent.learn(num_episodes=100)
parameters.builder.dataset(priority_exponent=0.6, max_priority_weight=0.9)
parameters.builder.policy(epsilon=0.01)
parameters_spec = parameters.to_spec()
pprint.pprint(parameters_spec)

# Output should be:
#
# {
#     "agent": {
#         "evaluate": {"num_episodes": 50},
#         "learn": {"num_episodes": 100},
#     },
#     "dataset": {
#         "__init__": {"priority_exponent": 0.6, "max_priority_weight": 0.9},
#     },
#     "policy": {
#         "__init__": {"epsilon": 0.01},
#     },
# }
