import pytest

from agentos.cli import run
from tests.utils import RLLIB_AGENT_DIR, run_test_command

test_args = ["agent"]
test_kwargs = {"--registry-file": str(RLLIB_AGENT_DIR / "components.yaml")}


def test_rllib_agent_evaluate(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "evaluate"
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)


def test_rllib_agent_learn(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "learn"
    kwargs["--arg-set-kwargs"] = "{'num_iterations': 5}"
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)
