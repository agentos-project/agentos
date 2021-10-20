from pathlib import Path
from tests.utils import run_component_in_dir


def test_sb3_agent(venv):
    agent_dir = (
        Path(__file__).parent.parent.parent / "example_agents" / "sb3_agent"
    )
    run_component_in_dir(
        agent_dir, venv, "agent", entry_points=["evaluate", "learn"]
    )
