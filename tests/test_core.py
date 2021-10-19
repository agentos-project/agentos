"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
import pytest
import subprocess
from pathlib import Path


def test_cli(tmpdir):
    subprocess.run(["agentos", "init"], cwd=tmpdir, check=True)
    expected_file_names = [
        "agent.py",
        "environment.py",
        "policy.py",
        "dataset.py",
        "trainer.py",
        "agentos.ini",
    ]
    for expected_file_name in expected_file_names:
        expected_path = Path(tmpdir) / expected_file_name
        assert expected_path.is_file(), f"{expected_file_name} not found"
    subprocess.run(
        ["agentos", "run", "agent", "-Pnum_episodes=10"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "run", "agent", "--entry-point=learn"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "run", "agent", "--entry-point=reset"],
        cwd=tmpdir,
        check=True,
    )