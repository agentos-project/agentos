"""Test suite for AgentOS Component."""
import pytest
from unittest.mock import patch
from unittest.mock import DEFAULT
from agentos.component import Component
from agentos.component_run import ComponentRun
from agentos.run_command import RunCommand
from utils import run_test_command, run_in_dir
from agentos.cli import init


# We define these classes at the module global level so that
# we can create components from them. Components cannot be
# created from classes that are defined within a function.
class SimpleAgent:
    def __init__(self):
        env_name = self.env.__class__.__name__
        print(f"SimpleAgent: AgentOS added self.env: {env_name}")

    def reset_env(self):
        self.env.reset()


class SimpleEnvironment:
    def reset(self):
        print("SimpleEnvironment.reset() called")


class GenericDependency:
    class_member = "class_member_val"

    def __init__(self):
        self.x = "x_val"


def test_component_repl_demo():
    # Generate Components from Classes
    agent_comp = Component.from_class(SimpleAgent)
    environment_comp = Component.from_class(SimpleEnvironment)
    instance_comp = Component.from_class(GenericDependency)
    class_comp_with_same_name = Component.from_class(
        GenericDependency, instantiate=False
    )
    class_comp_with_diff_name = Component.from_class(
        GenericDependency, instantiate=False, name="ClassDependency"
    )

    # Add dependencies to SimpleAgent
    agent_comp.add_dependency(environment_comp, attribute_name="env")
    agent_comp.add_dependency(instance_comp)
    with pytest.raises(Exception):
        agent_comp.add_dependency(class_comp_with_same_name)
    agent_comp.add_dependency(class_comp_with_diff_name)

    assert "GenericDependency" in agent_comp.dependencies.keys()
    inst_dep_obj = agent_comp.dependencies["GenericDependency"].get_object()
    assert type(inst_dep_obj) == GenericDependency
    assert inst_dep_obj.class_member == "class_member_val"
    assert inst_dep_obj.x == "x_val"

    assert "ClassDependency" in agent_comp.dependencies.keys()
    class_dep_obj = agent_comp.dependencies["ClassDependency"].get_object()
    assert type(class_dep_obj) == type
    assert class_dep_obj.class_member == "class_member_val"
    assert not hasattr(class_dep_obj, "x")
    assert class_dep_obj().x == "x_val"

    # Instantiate a SimpleAgent and run reset_env() method
    r = agent_comp.run("reset_env")
    assert type(r) == ComponentRun
    assert type(r.run_command) == RunCommand
    assert r.run_command.component == agent_comp
    assert r.run_command.entry_point == "reset_env"
    for params in r.run_command.parameter_set.to_spec().values():
        assert params == {}

    copy = ComponentRun(existing_run_id=r.identifier)
    assert copy.run_command == r.run_command
    assert copy._mlflow_run.to_dictionary() == r._mlflow_run.to_dictionary()


def test_component_freezing(tmpdir):
    with run_in_dir(tmpdir):
        run_test_command(init)
        c = Component.from_registry_file("components.yaml", "agent")
        with patch.multiple(
            "agentos.repo.Repo",
            get_version_from_git=DEFAULT,
            get_prefixed_path_from_repo_root=DEFAULT,
        ) as mocks:
            mocks["get_version_from_git"].return_value = (
                "https://example.com",
                "test_freezing_version",
            )
            mocks[
                "get_prefixed_path_from_repo_root"
            ].return_value = "freeze/test.py"
            reg = c.to_frozen_registry()
            agent_spec = reg.get_component_spec("agent", flatten=True)
            assert agent_spec["repo"] == "local_dir"
            assert agent_spec["version"] == "test_freezing_version"
