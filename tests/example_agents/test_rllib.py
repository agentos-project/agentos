from tests.utils import run_component_in_dir
from tests.utils import RLLIB_AGENT_DIR


def test_rllib_agent(venv):
    run_component_in_dir(
        RLLIB_AGENT_DIR,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=["", "-P num_iterations=5"],
    )
