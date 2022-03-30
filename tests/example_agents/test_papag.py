from agentos.cli import run
from tests.utils import PAPAG_AGENT_DIR, run_test_command

# Use CartPole because Atari ROM licensing issues break tests on Windows.
test_args = [
    "agent",
    "--use-outer-env",
    "-Anum_env_steps=1",
    "-Anum_processes=1",
    "-Aenv_name=CartPole-v1",
]

test_kwargs = {
    "--registry-file": str(PAPAG_AGENT_DIR / "components.yaml"),
    "--arg-set-file": str(PAPAG_AGENT_DIR / "a2c_pong_args.yaml"),
}


def test_papag_agent_evaluate():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "evaluate"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)


def test_papag_agent_learn():
    kwargs = {k: v for k, v in test_kwargs.items()}
    kwargs["--entry-point"] = "learn"
    run_test_command(cmd=run, cli_args=test_args, cli_kwargs=kwargs)
