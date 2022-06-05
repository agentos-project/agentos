import pytest

from agentos.cli import run
# from tests.utils import ACME_DQN_AGENT_DIR, is_linux, run_test_command
from tests.utils import ACME_DQN_AGENT_DIR, run_test_command

test_args = ["agent"]
test_kwargs = {
    "--registry-file": str(ACME_DQN_AGENT_DIR / "components.yaml"),
    "--arg-set-kwargs": "{'num_episodes': 1}",
}


# @pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
@pytest.mark.skip()
def test_acme_dqn_agent_evaluate(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "evaluate"
    kwargs["--arg-set-id"] = "evaluate_args"
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)


# @pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
@pytest.mark.skip()
def test_acme_dqn_agent_learn(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "learn"
    kwargs["--arg-set-id"] = "learn_args"
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)
