"""Test suite for AgentOS Registry."""
import pytest
from tests.utils import is_linux, RANDOM_AGENT_DIR, CHATBOT_AGENT_DIR
from agentos.registry import Registry
from agentos.component import Component
from agentos.utils import generate_dummy_dev_registry
from agentos import ParameterSet


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_registry_integration(venv):
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
    registry = Registry.from_dict(generate_dummy_dev_registry())
    component = Component.from_registry(registry, "acme_r2d2_agent")
    param_set = ParameterSet(params)
    component.run("evaluate", param_set)


def test_registry_from_dict():
    reg_dict = generate_dummy_dev_registry("test_key")
    reg_dict["components"]["acme_cartpole==master"] = {
        "class_name": "CartPole",
        "dependencies": {},
        "repo": "dev_repo",
    }
    r = Registry.from_dict(reg_dict)

    assert "acme_cartpole==test_key" in r.get_component_specs().keys()
    assert (
        "acme_cartpole==test_key"
        in r.get_component_specs(filter_by_name="acme_cartpole").keys()
    )
    assert (
        "acme_cartpole==master"
        in r.get_component_specs(filter_by_name="acme_cartpole").keys()
    )

    agent_component_flat_spec = r.get_component_spec(
        "acme_r2d2_agent", flatten=True
    )
    assert agent_component_flat_spec["name"] == "acme_r2d2_agent"
    assert agent_component_flat_spec["version"] == "test_key"
    assert agent_component_flat_spec["class_name"] == "AcmeR2D2Agent"
    assert agent_component_flat_spec["repo"] == "local_dir"


def test_registry_from_file():
    from agentos.exceptions import RegistryException
    from agentos.parameter_set import ParameterSet

    r = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    random_local_ag = Component.from_registry(r, "agent")
    assert random_local_ag.name == "agent"
    assert not random_local_ag.version
    assert random_local_ag.identifier.full == "agent"
    assert "environment" in random_local_ag.dependencies.keys()
    assert (
        random_local_ag.dependencies["environment"].identifier == "environment"
    )
    random_local_ag.run(
        "evaluate",
        ParameterSet({"agent": {"evaluate": {"num_episodes": 5}}}),
    )

    # Test publishing a component to an InMemoryRegistry
    chatbot_agent = Component.from_registry_file(
        CHATBOT_AGENT_DIR / "components.yaml", "chatbot"
    )
    assert chatbot_agent.class_name == "ChatBot"
    r.add_component(chatbot_agent)
    assert r.get_component_spec(chatbot_agent.name, chatbot_agent.version)
    assert r.get_component_spec("env_class")  # ensure dependencies got added.
    chatbot_agent.class_name = "NewClassName"
    with pytest.raises(RegistryException):
        r.add_component(chatbot_agent)
    r.add_component(chatbot_agent, force=True)
    updated = r.get_component_spec(
        chatbot_agent.name, chatbot_agent.version, flatten=True
    )
    assert updated["class_name"] == "NewClassName"

    reg_from_component = chatbot_agent.to_registry()
    assert reg_from_component.get_component_spec("chatbot")
    assert reg_from_component.get_component_spec("env_class")
