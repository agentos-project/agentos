from tests.utils import run_component_in_dir
from tests.utils import GH_SB3_AGENT_DIR


def test_sb3_agent(venv):
    run_component_in_dir(
        GH_SB3_AGENT_DIR,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=[
            "-Pn_eval_episodes=1",
            "-Ptotal_timesteps=100",
        ],
    )
