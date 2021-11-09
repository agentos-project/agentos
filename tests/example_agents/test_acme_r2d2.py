from tests.utils import run_component_in_dir
from tests.utils import ACME_R2D2_AGENT_DIR


def test_acme_r2d2_agent(venv):
    run_component_in_dir(
        ACME_R2D2_AGENT_DIR,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=[
            "--param-file parameters.yaml -Pnum_episodes=1",
            "--param-file parameters.yaml -Pnum_episodes=1",
        ],
    )
