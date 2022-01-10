from tests.utils import run_test_command
from tests.utils import RLLIB_AGENT_DIR
from agentos.cli import run

test_args = ["agent"]
test_kwargs = {"--registry-file": RLLIB_AGENT_DIR / "components.yaml"}


def test_rllib_agent_evaluate():
    test_kwargs["--entry-point"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)


def test_rllib_agent_learn():
    test_kwargs["--entry-point"] = "learn"
    test_kwargs["-P"] = "num_iterations=5"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)
