"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
from pathlib import Path
from utils import run_test_command
from utils import run_in_dir
from utils import SB3_AGENT_DIR
from agentos.cli import init, run, freeze, status


def test_cli_init(tmpdir):
    with run_in_dir(tmpdir):
        run_test_command(init)
        expected_file_names = [
            "agent.py",
            "environment.py",
            "policy.py",
            "dataset.py",
            "trainer.py",
            "components.yaml",
        ]
        for expected_file_name in expected_file_names:
            expected_path = Path(tmpdir) / expected_file_name
            assert expected_path.is_file(), f"{expected_file_name} not found"
        # Test basic run commands work on initialized agent
        run_args = ["agent"]
        run_1_kwargs = {"-P": "num_episodes=1"}
        run_test_command(run, cli_args=run_args, cli_kwargs=run_1_kwargs)
        run_2_kwargs = {"--entry-point": "learn"}
        run_test_command(run, cli_args=run_args, cli_kwargs=run_2_kwargs)


def test_cli_run():
    with run_in_dir(SB3_AGENT_DIR):
        run_test_command(status)
        run_args = ["agent"]
        run_test_command(status, cli_args=run_args)


def test_cli_status(tmpdir):
    pass


def test_cli_freeze(tmpdir):
    run_args = ["agent", "-f"]
    run_kwargs = {"--registry-file": SB3_AGENT_DIR / "components.yaml"}
    run_test_command(freeze, cli_args=run_args, cli_kwargs=run_kwargs)
