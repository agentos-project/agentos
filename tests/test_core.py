"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
import os
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
            "README.md",
            "components.yaml",
            "requirements.txt",
        ]
        for file_name in os.listdir():
            error_msg = f"Unexpected file created by agentos init: {file_name}"
            print(file_name)
            print(expected_file_names)
            print(file_name in expected_file_names)
            assert file_name in expected_file_names, error_msg
        for expected_file_name in expected_file_names:
            expected_path = Path(tmpdir) / expected_file_name
            assert expected_path.is_file(), f"{expected_file_name} not found"
        # Test basic run commands work on initialized agent
        run_args = ["agent"]
        run_1_kwargs = {}
        run_test_command(run, cli_args=run_args, cli_kwargs=run_1_kwargs)
        run_2_kwargs = {"-P": "num_episodes=10"}
        run_test_command(run, cli_args=run_args, cli_kwargs=run_2_kwargs)


def test_cli_status():
    with run_in_dir(SB3_AGENT_DIR):
        run_test_command(status)
        run_args = ["sb3_agent", "--use-outer-env"]
        run_test_command(status, cli_args=run_args)


def test_cli_freeze(tmpdir):
    run_args = ["sb3_agent", "-f", "--use-outer-env"]
    run_kwargs = {"--registry-file": str(SB3_AGENT_DIR / "components.yaml")}
    run_test_command(freeze, cli_args=run_args, cli_kwargs=run_kwargs)
