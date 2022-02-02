import pytest
from agentos.registry import WebRegistry
# from agentos.component import Component
from agentos.repo import Repo

agentos_repo_spec = {
    "AgentOSRepo": {
        "type": "github",
        "url": "https://github.com/agentos-project/agentos.git",
    }
}

agentos_repo = Repo.from_spec(agentos_repo_spec)


class SimpleComponent:
    pass


@pytest.mark.skip(reason="Acme only available on posix")
def test_web_registry():
    web_registry = WebRegistry("http://localhost:8000/api/v1")

    web_registry.add_repo_spec(agentos_repo_spec)

    # Test fetching a repo_spec [spec]
    flat_repo_spec = web_registry.get_repo_spec("AgentOSRepo", flatten=True)
    assert len(flat_repo_spec) == 3
    print(flat_repo_spec)
    assert flat_repo_spec["identifier"] == "AgentOSRepo"
    assert flat_repo_spec["type"] == "github"
    assert flat_repo_spec["url"] == (
        "https://github.com/agentos-project/agentos.git"
    )

    nested_repo_spec = web_registry.get_repo_spec("AgentOSRepo")
    assert nested_repo_spec["AgentOSRepo"]["type"] == "github"
    repo = Repo.from_spec(nested_repo_spec)
    assert repo.identifier == "AgentOSRepo"

    # TODO: Finish writing this test and porting WebRegistry funtionality to
    #       the new Registry design.
    # simple_component_spec = Component.from_repo(
    #    repo,
    #    identifier="SimpleComponent==test_staging",
    #    class_name="SimpleComponent",
    #    file_path="tests/test_web_registry.py"
    # )
    # assert simple_component_spec["repo"] == "AgentOSRepo"

    # web_registry.add_component_spec(simple_component_spec)

    # comp = web_registry.get_component_spec(
    #    name="SimpleComponent", version="1234", flatten=True
    # )
    # assert comp["name"] == "SimpleComponent"
    # assert comp["repo"] == "SimpleRepo"

    # c = Component.from_class(Simple)
    # web_registry.add_component(c)
