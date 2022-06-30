import pytest

from agentos.cli import run
from tests.utils import PAPAG_AGENT_DIR, is_windows, run_test_command

# Use CartPole because Atari ROM licensing issues break tests on Windows.
test_args = [
    "a2c_cartpole_papag_agent",
    "--arg-set-kwargs",
    "{'num_env_steps': 1, 'num_processes': 1}",
    "--registry-file",
    str(PAPAG_AGENT_DIR / "components.yaml"),
    "--registry-file",
    str(PAPAG_AGENT_DIR / "a2c_cartpole_args.yaml"),
]


@pytest.mark.skipif(is_windows(), reason="See issue #417, bad symlinks")
def test_papag_agent_evaluate(cli_runner):
    kwargs = {
        "--function-name": "evaluate",
        "--arg-set-id": "evaluation_args",
    }
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)


@pytest.mark.skipif(is_windows(), reason="See issue #417, bad symlinks")
def test_papag_agent_learn(cli_runner):
    kwargs = {
        "--function-name": "learn",
        "--arg-set-id": "a2c_cartpole_learn_args",
    }
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)
