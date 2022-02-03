from tests.utils import run_test_command
from tests.utils import SB3_AGENT_DIR
from agentos.cli import run

test_args = ["sb3_agent"]
test_kwargs = {"--registry-file": str(SB3_AGENT_DIR / "components.yaml")}


def test_sb3_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "evaluate"
    kwargs["-P"] = "n_eval_episodes=1"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


def test_sb3_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "learn"
    kwargs["-P"] = "total_timesteps=100"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
