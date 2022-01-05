import pytest
from tests.utils import run_test_command
from tests.utils import is_linux
from agentos.cli import run

component_name = "agent"
test_args = {
    "--registry-file": "example_agents/acme_r2d2/components.yaml",
    "-P": "num_episodes=1",
    "--param-file": "example_agents/acme_r2d2/parameters.yaml",
}


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_r2d2_agent_evaluate():
    test_args["--entry-point"] = "evaluate"
    run_test_command(cmd=run, component_name=component_name, args=test_args)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_r2d2_agent_learn():
    test_args["--entry-point"] = "learn"
    run_test_command(cmd=run, component_name=component_name, args=test_args)
