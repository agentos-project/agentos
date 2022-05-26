"""Test suite for AgentOS Registry."""
import pytest

from pcs import Module
from pcs.argument_set import ArgumentSet
from pcs.component import Component
from pcs.registry import Registry
from pcs.repo import Repo
from pcs.utils import generate_dummy_dev_registry, make_identifier_ref
from tests.utils import (
    CHATBOT_AGENT_DIR,
    RANDOM_AGENT_DIR,
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
    is_linux,
)


def test_resolve_inline_specs():
    inner_spec_body = {"type": "Module", "key": "val"}

    def get_outer_spec_body(what_to_inline):
        return {"type": "Class", "some_module": what_to_inline}

    inner_spec_id = Component.spec_body_to_identifier(inner_spec_body)
    normalized_outer = get_outer_spec_body(make_identifier_ref(inner_spec_id))
    nested_outer = get_outer_spec_body(inner_spec_body)
    normalized_outer_id = Component.spec_body_to_identifier(normalized_outer)
    r = Registry.from_dict({"specs": {normalized_outer_id: nested_outer}})
    outer_id = r.get_spec(normalized_outer_id, flatten=True)["some_module"]
    assert outer_id == make_identifier_ref(inner_spec_id)
    assert r.get_spec(inner_spec_id, flatten=True)["type"] == "Module"


def test_resolve_inline_aliases():
    test_reg_dict = {"specs": {"inline_alias": {"type": "Module", "k": "v"}}}
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

    r = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    random_local_ag = Module.from_registry(r, "agent")
    assert "environment" in random_local_ag.argument_set.kwargs
    random_local_ag.run_with_arg_set(
        "run_episodes", ArgumentSet(kwargs={"num_episodes": 5})
    )

    # Test publishing a component to an InMemoryRegistry
    chatbot_agent = Module.from_registry_file(
        CHATBOT_AGENT_DIR / "components.yaml", "chatbot"
    )
    r.add_component(chatbot_agent)

    reg_from_component = chatbot_agent.to_registry()
    assert reg_from_component.get_spec(chatbot_agent.identifier)


def test_registry_from_repo():
    repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    reg = Registry.from_repo_inferred(
        repo,
        requirements_file="dev-requirements.txt",
        version=TESTING_BRANCH_NAME,
    )
    assert "pcs/component.py" in [
        body["file_path"] for body in reg.specs.values() if "file_path" in body
    ]
