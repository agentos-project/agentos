from tests.utils import run_test_command
from tests.utils import GH_SB3_AGENT_DIR
from agentos.cli import run

component_name = "agent"
test_args = {"--registry-file": GH_SB3_AGENT_DIR / "components.yaml"}


def test_sb3_agent_evaluate():
    test_args["--entry-point"] = "evaluate"
    test_args["-P"] = "n_eval_episodes=1"
    run_test_command(cmd=run, component_name=component_name, args=test_args)


def test_sb3_agent_learn():
    test_args["--entry-point"] = "learn"
    test_args["-P"] = "total_timesteps=100"
    run_test_command(cmd=run, component_name=component_name, args=test_args)
