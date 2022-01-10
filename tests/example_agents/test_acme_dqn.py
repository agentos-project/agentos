import pytest
from tests.utils import run_test_command
from tests.utils import is_linux
from tests.utils import ACME_DQN_AGENT_DIR
from agentos.cli import run

test_args = ["agent"]
test_kwargs = {
    "--registry-file": str(ACME_DQN_AGENT_DIR / "components.yaml"),
    "-P": "num_episodes=1",
    "--param-file": str(ACME_DQN_AGENT_DIR / "parameters.yaml"),
}


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "learn"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
