import pytest
from pathlib import Path
from tests.utils import run_component_in_dir


def test_rllib_agent(venv):
    agent_dir = Path(__file__).parent.parent.parent / "example_agents" / "rllib_agent"
    run_component_in_dir(
        agent_dir,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=["", "-P num_iterations=5"],
    )


