import pytest
from tests.utils import run_test_command
from tests.utils import is_linux
from tests.utils import ACME_DQN_AGENT_DIR
from agentos.cli import run

test_args = ["agent"]
test_kwargs = {
    "--registry-file": ACME_DQN_AGENT_DIR / "components.yaml",
    "-P": "num_episodes=1",
    "--param-file": ACME_DQN_AGENT_DIR / "parameters.yaml",
}


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_evaluate():
    test_args["--entry-point"] = "evaluate"
    run_test_command(cmd=run, args=test_args, kwargs=test_kwargs)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent_learn():
    test_args["--entry-point"] = "learn"
    run_test_command(cmd=run, args=test_args, kwargs=test_kwargs)
