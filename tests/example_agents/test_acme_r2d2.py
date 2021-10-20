from pathlib import Path
from tests.utils import run_component_in_dir


def test_acme_r2d2_agent(venv):
    agent_dir = (
        Path(__file__).parent.parent.parent / "example_agents" / "acme_r2d2"
    )
    run_component_in_dir(
        agent_dir,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=[
            "--param-file parameters.yaml",
            "--param-file parameters.yaml",
        ],
    )
