"""Test suite for AgentOS Registry."""
import pytest
from tests.utils import ACME_R2D2_AGENT_DIR
from tests.utils import install_requirements
from tests.utils import run_code_in_venv
from tests.utils import is_linux


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_module_level_registry(venv):
    install_requirements(ACME_R2D2_AGENT_DIR, venv, "requirements.txt")
    code = "import agentos\n" "agentos.get_component('acme_r2d2_agent')"
    run_code_in_venv(venv, code)


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_registry_integration(venv):
    install_requirements(ACME_R2D2_AGENT_DIR, venv, "requirements.txt")
    params = {
        "acme_r2d2_agent": {
            "evaluate": {"num_episodes": 10},
            "learn": {"num_episodes": 10},
        },
        "acme_r2d2_dataset": {
            "__init__": {
                "batch_size": 32,
                "discount": 0.99,
                "max_priority_weight": 0.9,
                "max_replay_size": 500,
                "priority_exponent": 0.6,
                "replay_period": 40,
                "sequence_length": 13,
                "store_lstm_state": True,
            }
        },
        "acme_cartpole": {
            "__init__": {
                "batch_size": 32,
                "discount": 0.99,
                "max_replay_size": 500,
                "replay_period": 40,
                "sequence_length": 13,
                "store_lstm_state": True,
            }
        },
        "acme_r2d2_policy": {
            "__init__": {
                "batch_size": 32,
                "discount": 0.99,
                "epsilon": 0.01,
                "max_replay_size": 500,
                "replay_period": 40,
                "sequence_length": 13,
                "store_lstm_state": True,
            }
        },
        "acme_r2d2_trainer": {
            "__init__": {
                "adam_epsilon": 0.001,
                "batch_size": 32,
                "burn_in_length": 2,
                "clip_grad_norm": None,
                "discount": 0.99,
                "importance_sampling_exponent": 0.2,
                "learning_rate": 0.001,
                "max_replay_size": 500,
                "min_replay_size": 50,
                "n_step": 5,
                "replay_period": 40,
                "samples_per_insert": 32.0,
                "sequence_length": 13,
                "store_lstm_state": True,
                "target_update_period": 20,
            }
        },
    }
    code = (
        "from agentos.registry import Registry\n"
        "from agentos import ParameterSet\n"
        "registry = Registry()\n"
        "component = registry.get_component('acme_r2d2_agent')\n"
        f"params = ParameterSet({params})\n"
        "component.run('evaluate', params)\n"
    )
    run_code_in_venv(venv, code)


def test_registry_from_dict():
    from agentos.registry import Registry
    from agentos.utils import DUMMY_DEV_REGISTRY_DICT
    from agentos.component import Component

    r = Registry.from_dict(DUMMY_DEV_REGISTRY_DICT)
    assert "acme_cartpole==nj_registry_2next" in r.components().keys()
    assert (
        "acme_cartpole==nj_registry_2next"
        in r.components(filter_by_name="acme_cartpole").keys()
    )
    assert (
        "acme_cartpole==master"
        in r.components(filter_by_name="acme_cartpole").keys()
    )
    c = Component.from_registry(r, "sb3_ppo_agent")
    assert c.name == "sb3_ppo_agent"
    assert c.version == "nj_registry_2next"
    assert c.identifier == "sb3_ppo_agent==nj_registry_2next"
    assert "environment" in c.dependencies.keys()
    assert (
        c.dependencies["environment"].full_name
        == "sb3_cartpole==nj_registry_2next"
    )
