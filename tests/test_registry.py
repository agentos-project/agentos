"""Test suite for AgentOS Registry."""
import pytest

from pcs.argument_set import ArgumentSet
from pcs.component import Module
from pcs.registry import Registry
from pcs.repo import Repo
from pcs.spec_object import Component
from pcs.utils import generate_dummy_dev_registry
from tests.utils import (
    CHATBOT_AGENT_DIR,
    RANDOM_AGENT_DIR,
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
    is_linux,
)


def test_resolve_inline_specs():
    outer_spec_body = {
        "argument_set":
            {
                "type": "Module",
                "key": "val"
           }
        }
    outer_spec_id = Component.spec_body_to_identifier(outer_spec_body)
    r = Registry.from_dict({"specs": {outer_spec_id: outer_spec_body}})
    arg_set_id = r.get_spec(outer_spec_id, flatten=True)["argument_set"]
    assert r.get_spec(arg_set_id, flatten=True)["type"] == "Module"


def test_resolve_inline_aliases():
    test_reg_dict = {
        "specs":
            {
                "inline_alias":
                    {
                        "type": "Module",
                        "k": "v"
                    }
            }
    }
    r = Registry.from_dict(test_reg_dict)
    spec_id = r.aliases["inline_alias"]
    assert r.get_spec(spec_id, flatten=True)["k"] == "v"
    assert r.get_spec("inline_alias", flatten=True)["k"] == "v"


@pytest.mark.skipif(not is_linux(), reason="Acme only available on posix")
def test_registry_integration(venv):
    args = {
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
    component = Module.from_registry(
        registry, "acme_r2d2_agent", use_venv=False
    )
    component.run_with_arg_set("evaluate", ArgumentSet(args))


def test_registry_from_dict():
    reg_dict = generate_dummy_dev_registry("test_key")
    reg_dict["components"]["acme_cartpole==master"] = {
        "name": "CartPole",
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
    assert agent_component_flat_spec["name"] == "AcmeR2D2Agent"
    assert agent_component_flat_spec["repo"] == "local_dir"


def test_registry_from_file():
    from pcs.argument_set import ArgumentSet
    from pcs.exceptions import RegistryException

    r = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    random_local_ag = Module.from_registry(r, "agent")
    assert random_local_ag.name == "agent"
    assert not random_local_ag.version
    assert random_local_ag.identifier == "agent"
    assert "environment" in random_local_ag.dependencies().keys()
    assert (
        random_local_ag.dependencies()["environment"].identifier == "environment"
    )
    random_local_ag.run_with_arg_set(
        "run_episodes",
        ArgumentSet({"agent": {"run_episodes": {"num_episodes": 5}}}),
    )

    # Test publishing a component to an InMemoryRegistry
    chatbot_agent = Module.from_registry_file(
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
    assert updated["name"] == "NewClassName"

    reg_from_component = chatbot_agent.to_registry()
    assert reg_from_component.get_component_spec("chatbot")
    assert reg_from_component.get_component_spec("env_class")


def test_registry_from_repo():
    repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    reg = Registry.from_repo_inferred(
        repo,
        requirements_file="dev-requirements.txt",
        version=TESTING_BRANCH_NAME,
    )
    comp_name = f"module:pcs__component.py=={TESTING_BRANCH_NAME}"
    assert comp_name in reg.to_dict()["components"]
