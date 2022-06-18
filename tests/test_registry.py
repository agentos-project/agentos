"""Test suite for AgentOS Registry."""

import pprint

import yaml

from pcs import Module
from pcs.registry import Registry
from pcs.repo import Repo
from pcs.specs import Spec
from pcs.utils import extract_identifier, is_identifier, make_identifier_ref
from tests.utils import (
    CHATBOT_AGENT_DIR,
    RANDOM_AGENT_DIR,
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
)


def test_resolve_inline_specs():
    test_spec_dict = {
        "outer_spec": {
            "type": "ArgumentSet",
            "args": [{"inner_spec": {"type": "LocalRepo", "path": "."}}],
        }
    }
    r = Registry.from_dict({"specs": test_spec_dict})

    outer = r.get_spec("outer_spec")
    inner_id = extract_identifier(outer.body["args"][0])
    assert inner_id in r
    assert inner_id in r.specs
    assert r.get_spec(inner_id).to_flat()["type"] == "LocalRepo"


def test_resolve_inline_aliases():
    test_reg_dict = {
        "specs": {
            "inline_alias": {
                "type": "ArgumentSet",
                "kwargs": {"repo": "spec:other_spec"},
            },
            "other_spec": {"type": "LocalRepo", "path": "."},
        }
    }
    r = Registry.from_dict(test_reg_dict)
    assert "inline_alias" in r.aliases
    spec_id = r.aliases["inline_alias"]
    assert is_identifier(spec_id)
    assert r.get_spec(spec_id, flatten=True)["type"] == "ArgumentSet"
    flat_spec = r.get_spec("inline_alias", flatten=True)
    assert flat_spec["type"] == "ArgumentSet"
    # Check that uses of aliases in spec bodies are replaced with specs
    assert flat_spec["kwargs"]["repo"] == make_identifier_ref(
        r.aliases["other_spec"]
    )


def test_registry_from_file():
    from pcs.argument_set import ArgumentSet

    r = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    random_local_ag = Module.from_registry(r, "agent")
    assert "environment_cls" in random_local_ag.argument_set.kwargs
    random_local_ag.run_with_arg_set(
        "evaluate", ArgumentSet(kwargs={"num_episodes": 5})
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


def test_triangle_dependency_graphs():
    registry_yaml = """
specs:
    one:
        type: LocalRepo
        path: .
    two:
        type: ArgumentSet
        args:
            - spec:one
            - this is two
    three:
        type: ArgumentSet
        args:
            - spec:one
            - this is three
    four:
        type: ArgumentSet
        args:
            - spec:two
            - spec:three
"""
    reg = Registry.from_dict(yaml.load(registry_yaml))
    pprint.pprint(reg.to_dict())
    replacement_spec = Spec.from_flat({"type": "LocalRepo", "path": "/tmp"})
    reg.replace_spec("one", replacement_spec)
    assert reg.get_spec("one").to_flat()["path"] == "/tmp"
