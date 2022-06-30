import pytest

from agentos.cli import run
from tests.utils import SB3_AGENT_DIR, is_windows, run_test_command

test_args = ["sb3_agent"]
test_kwargs = {"--registry-file": str(SB3_AGENT_DIR / "components.yaml")}


@pytest.mark.skipif(is_windows(), reason="See issue #417, bad symlinks")
def test_sb3_agent_evaluate(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "evaluate"
    kwargs["--arg-set-kwargs"] = '{"n_eval_episodes": 1}'
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)


@pytest.mark.skipif(is_windows(), reason="See issue #417, bad symlinks")
def test_sb3_agent_learn(cli_runner):
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "learn"
    kwargs["--arg-set-kwargs"] = '{"total_timesteps": 100}'
    run_test_command(cli_runner, run, cli_args=test_args, cli_kwargs=kwargs)
