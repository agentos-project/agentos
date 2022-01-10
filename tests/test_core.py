"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
import os
from pathlib import Path
from utils import run_test_command
from agentos.cli import init, run



def test_cli(tmpdir):
    curr_dir = os.getcwd()
    os.chdir(tmpdir)
    try:
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

        run_1_params = {'-P': 'num_episodes=1'}
        run_test_command(run, component_name='agent', args=run_1_params)
        run_2_params = {'--entry-point': 'learn'}
        run_test_command(run, component_name='agent', args=run_2_params)
        run_3_params = {'--entry-point': 'reset'}
        run_test_command(run, component_name='agent', args=run_3_params)
    finally:
        os.chdir(curr_dir)
