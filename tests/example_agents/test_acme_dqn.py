import pytest

from agentos.cli import run
from tests.utils import ACME_DQN_AGENT_DIR, is_linux, run_test_command

test_args = ["agent", "--use-outer-env"]
test_kwargs = {
    "--registry-file": str(ACME_DQN_AGENT_DIR / "components.yaml"),
    "-A": "num_episodes=1",
    "--arg-set-file": str(ACME_DQN_AGENT_DIR / "arguments.yaml"),
}


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "learn"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
