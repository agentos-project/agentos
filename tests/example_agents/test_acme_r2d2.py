import pytest
from tests.utils import run_test_command
from tests.utils import is_linux
from tests.utils import ACME_R2D2_AGENT_DIR
from agentos.cli import run

test_args = ["agent"]
test_kwargs = {
    "--registry-file": ACME_R2D2_AGENT_DIR / "components.yaml",
    "-P": "num_episodes=1",
    "--param-file": ACME_R2D2_AGENT_DIR / "parameters.yaml",
}


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_r2d2_agent_evaluate():
    test_kwargs["--entry-point"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_r2d2_agent_learn():
    test_kwargs["--entry-point"] = "learn"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)
