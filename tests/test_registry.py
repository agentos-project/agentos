"""Test suite for AgentOS Registry."""
import pytest
from tests.utils import is_linux
from agentos.registry import Registry
from agentos.component import Component
from agentos.utils import DUMMY_WEB_REGISTRY_DICT
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
    registry = Registry.from_dict(DUMMY_WEB_REGISTRY_DICT)
    component = Component.from_registry(registry, "acme_r2d2_agent")
    param_set = ParameterSet(params)
    component.run("evaluate", param_set)


def test_registry_from_dict():
    from agentos.registry import Registry, RegistryException
    from agentos.utils import DUMMY_WEB_REGISTRY_DICT
    from agentos.component import Component
    from agentos.parameter_set import ParameterSet

    r = Registry.from_dict(DUMMY_WEB_REGISTRY_DICT)

    assert (
        "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f"
        in r.get_component_specs().keys()
    )
    assert (
        "acme_cartpole==fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f"
        in r.get_component_specs(filter_by_name="acme_cartpole").keys()
    )
    assert (
        "acme_cartpole==master"
        in r.get_component_specs(filter_by_name="acme_cartpole").keys()
    )

    agent_component_flat_spec = r.get_component_spec("acme_r2d2_agent")
    assert agent_component_flat_spec["name"] == "acme_r2d2_agent"
    assert (
        agent_component_flat_spec["version"]
        == "fe150c5ea8ee6e2e6c1dbbfc85cb53b85f19c55f"
    )
    assert agent_component_flat_spec["class_name"] == "AcmeR2D2Agent"
    assert agent_component_flat_spec["repo"] == "dev_repo"

    # Test retrieving a component from an InMemoryRegistry.
    c = Component.from_registry(r, "random_agent")
    assert c.name == "random_agent"
    assert c.version == "for_tests_dummy_dev_registry"
    assert c.identifier == "random_agent==for_tests_dummy_dev_registry"
    assert "environment" in c.dependencies.keys()
    assert (
        c.dependencies["environment"].identifier
        == "random_corridor==for_tests_dummy_dev_registry"
    )
    random_local_ag = Component.from_registry(
        Registry.from_yaml("example_agents/random/components.yaml"), "agent"
    )
    random_local_ag.run(
        "evaluate",
        ParameterSet({"agent": {"evaluate": {"num_episodes": 5}}}),
    )

    # Test publishing a component to an InMemoryRegistry
    chatbot_agent = Component.from_registry_file(
        "example_agents/chatbot/components.yaml", "chatbot"
    )
    assert chatbot_agent.class_name == "ChatBot"
    r.add_component(chatbot_agent)
    assert r.get_component_spec(chatbot_agent.name, chatbot_agent.version)
    assert r.get_component_spec("env_class")  # ensure dependencies got added.
    chatbot_agent.class_name = "NewClassName"
    with pytest.raises(RegistryException):
        r.add_component(chatbot_agent)
    r.add_component(chatbot_agent, force=True)
    updated = r.get_component_spec(chatbot_agent.name, chatbot_agent.version)
    assert updated["class_name"] == "NewClassName"

    reg_from_component = chatbot_agent.to_registry()
    assert reg_from_component.get_component_spec("chatbot")
    assert reg_from_component.get_component_spec("env_class")
