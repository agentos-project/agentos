import pytest
from tests.utils import run_component_in_dir
from tests.utils import ACME_DQN_AGENT_DIR
from tests.utils import is_linux


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_dqn_agent(venv):
    run_component_in_dir(
        ACME_DQN_AGENT_DIR,
        venv,
        "agent",
        entry_points=["evaluate", "learn"],
        entry_point_params=[
            "--param-file parameters.yaml -Pnum_episodes=1",
            "--param-file parameters.yaml -Pnum_episodes=1",
        ],
    )
