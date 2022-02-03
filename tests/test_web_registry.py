import pytest
from agentos.registry import WebRegistry
from agentos.component import Component
from agentos.repo import Repo

agentos_repo_spec = {
    "AgentOSRepo": {
        "type": "github",
        "url": "https://github.com/agentos-project/agentos.git",
    }
}
agentos_component_spec = {
    "AgentOSComponent": {
        "repo": "AgentOSRepo",
        "class_name": "SimpleComponent",
        "file_path": "tests/test_web_registry.py",
        "instantiate": True,
    }
}

agentos_repo = Repo.from_spec(agentos_repo_spec)


class SimpleComponent:
    def __init__(self, init_member=1):
        self.init_member = init_member

    def add_to_init_member(self, i=1):
        return self.init_member + i


@pytest.mark.skip(
    reason=(
        "Currently requires dev to setup & run the webapp and ensure "
        "that the test components do not exist in the registry server."
    )
)
def test_web_registry():
    web_registry = WebRegistry("http://localhost:8000/api/v1")

    # Test adding a repo_spec.
    web_registry.add_repo_spec(agentos_repo_spec)

    # Test fetching a flattened repo_spec.
    flat_repo_spec = web_registry.get_repo_spec("AgentOSRepo", flatten=True)
    assert len(flat_repo_spec) == 3
    print(flat_repo_spec)
    assert flat_repo_spec["identifier"] == "AgentOSRepo"
    assert flat_repo_spec["type"] == "github"
    assert flat_repo_spec["url"] == (
        "https://github.com/agentos-project/agentos.git"
    )

    # Test fetching a unflattened (i.e., nested) repo_spec.
    nested_repo_spec = web_registry.get_repo_spec("AgentOSRepo")
    assert nested_repo_spec["AgentOSRepo"]["type"] == "github"
    repo = Repo.from_spec(nested_repo_spec)
    assert repo.identifier == "AgentOSRepo"

    # Test adding a component that we generate from the repo.
    simple_component = Component.from_repo(
        repo,
        identifier="SimpleComponent==test_staging",
        class_name="SimpleComponent",
        file_path="tests/test_web_registry.py",
    )
    assert simple_component.repo.identifier == "AgentOSRepo"

    web_registry.add_component_spec(simple_component.to_spec())

    # Test getting a flattened component (i.e., the one we just added)
    comp = web_registry.get_component_spec(
        name="SimpleComponent", version="test_staging", flatten=True
    )
    assert comp["name"] == "SimpleComponent"
    assert comp["repo"] == "AgentOSRepo"

    # Test getting an unflattened component (i.e., the one we just added)
    comp = web_registry.get_component_spec(
        name="SimpleComponent", version="test_staging", flatten=False
    )
    assert comp["SimpleComponent"]["class_name"] == "SimpleComponent"
    assert comp["SimpleComponent"]["repo"] == "AgentOSRepo"

    # Test adding a ComponentRun
    param_set = {"SimpleComponent": {"add_to_init_member": {"i": 10}}}
    comp_run = simple_component.run("SimpleComponent", param_set)
    web_registry.add_run_command_spec(comp_run.run_command)


# TODO: add a test that publishes a ComponentRun or Compoonent from the CLI.
# def test_web_registry_from_cli():
#     from tests.utils import run_test_command
#     run_test_command()
