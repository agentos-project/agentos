from tests.utils import run_test_command
from agentos.cli import run

component_name = "agent"
test_args = {"--registry-file": "example_agents/rllib_agent/components.yaml"}


def test_rllib_agent_evaluate():
    test_args["--entry-point"] = "evaluate"
    run_test_command(cmd=run, component_name=component_name, args=test_args)


def test_rllib_agent_learn():
    test_args["--entry-point"] = "learn"
    test_args["-P"] = "num_iterations=5"
    run_test_command(cmd=run, component_name=component_name, args=test_args)
