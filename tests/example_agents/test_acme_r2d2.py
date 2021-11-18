import pytest
from tests.utils import run_component_in_dir
from tests.utils import ACME_R2D2_AGENT_DIR
from tests.utils import is_linux


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_acme_r2d2_agent(venv):
    run_component_in_dir(
        dir_name=ACME_R2D2_AGENT_DIR,
        venv=venv,
        component_name="agent",
        agentos_cmd="run",
        entry_points=["evaluate", "learn"],
        entry_point_params=[
            "--param-file parameters.yaml -Pnum_episodes=1",
            "--param-file parameters.yaml -Pnum_episodes=1",
        ],
    )
