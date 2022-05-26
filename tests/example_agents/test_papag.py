from agentos.cli import run
from tests.utils import PAPAG_AGENT_DIR, run_test_command

# Use CartPole because Atari ROM licensing issues break tests on Windows.
test_args = [
    "papag_agent",
    "-K {'num_env_steps': 1, 'num_processes': 1}",
    "--registry-file",
    str(PAPAG_AGENT_DIR / "components.yaml"),
    "--registry-file",
    str(PAPAG_AGENT_DIR / "a2c_cartpole_args.yaml"),
]

test_kwargs = {"--arg-set-id": "a2c_cartpole_args"}


def test_papag_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


def test_papag_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--function-name"] = "learn"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
