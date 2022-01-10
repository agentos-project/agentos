"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
from pathlib import Path
from utils import run_test_command, run_in_dir, RANDOM_AGENT_DIR
from agentos.cli import init, run


def test_cli_init(tmpdir):
    with run_in_dir(tmpdir):
        run_test_command(init)
        expected_file_names = [
            "agent.py",
            "environment.py",
            "policy.py",
            "dataset.py",
            "trainer.py",
            "run_manager.py",
            "components.yaml",
        ]
        for expected_file_name in expected_file_names:
            expected_path = Path(tmpdir) / expected_file_name
            assert expected_path.is_file(), f"{expected_file_name} not found"
        # Test basic run commands work on initialized agent
        run_1_params = {"-P": "num_episodes=1"}
        run_test_command(run, component_name="agent", args=run_1_params)
        run_2_params = {"--entry-point": "learn"}
        run_test_command(run, component_name="agent", args=run_2_params)
        run_3_params = {"--entry-point": "reset"}
        run_test_command(run, component_name="agent", args=run_3_params)


def test_cli_run(tmpdir):
    with run_in_dir(tmpdir):
        run_params = {
            "-P": "num_episodes=1",
            "--entry-point": "evaluate",
            "--registry-file": RANDOM_AGENT_DIR / "components.yaml",
        }
        run_test_command(run, component_name="agent", args=run_params)


def test_cli_status(tmpdir):
    raise Exception()


def test_cli_freeze(tmpdir):
    raise Exception()
