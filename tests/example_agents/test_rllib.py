from agentos.cli import run
from tests.utils import RLLIB_AGENT_DIR, run_test_command

test_args = ["agent", "--use-outer-env"]
test_kwargs = {"--registry-file": str(RLLIB_AGENT_DIR / "components.yaml")}


def test_rllib_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


def test_rllib_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "learn"
    kwargs["-A"] = "num_iterations=5"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
