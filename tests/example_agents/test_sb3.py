from tests.utils import run_test_command
from tests.utils import SB3_AGENT_DIR
from agentos.cli import run

test_args = ["agent"]
test_kwargs = {"--registry-file": str(SB3_AGENT_DIR / "components.yaml")}


def test_sb3_agent_evaluate():
    test_kwargs["--entry-point"] = "evaluate"
    test_kwargs["-P"] = "n_eval_episodes=1"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)


def test_sb3_agent_learn():
    test_kwargs["--entry-point"] = "learn"
    test_kwargs["-P"] = "total_timesteps=100"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=test_kwargs)
