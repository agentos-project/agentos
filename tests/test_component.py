"""Test suite for AgentOS Component."""
from unittest.mock import DEFAULT, patch

import pytest
from utils import run_in_dir, run_test_command

from agentos.cli import init
from agentos.component import Component
from agentos.component_run import ComponentRun
from agentos.repo import Repo
from agentos.run_command import RunCommand
from agentos.virtual_env import auto_revert_venv
from tests.utils import (
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
)


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
    agent_comp = Component.from_class(SimpleAgent, instantiate=True)
    environment_comp = Component.from_class(
        SimpleEnvironment, instantiate=True
    )
    instance_comp = Component.from_class(GenericDependency, instantiate=True)
    class_comp_with_same_name = Component.from_class(
        GenericDependency, instantiate=False
    )
    class_comp_with_diff_name = Component.from_class(
        GenericDependency,
        identifier="ClassDependency",
        instantiate=False,
    )

    # Add dependencies to SimpleAgent
    agent_comp.add_dependency(environment_comp, attribute_name="env")
    agent_comp.add_dependency(instance_comp)
    with pytest.raises(Exception):
        # Ensure adding a dependency with same identifier raises exception.
        agent_comp.add_dependency(class_comp_with_same_name)
    agent_comp.add_dependency(class_comp_with_diff_name)

    assert "GenericDependency" in agent_comp.dependencies.keys()
    inst_dep_obj = agent_comp.dependencies["GenericDependency"].get_object()
    assert inst_dep_obj.__class__.__name__ == "GenericDependency"
    assert inst_dep_obj.class_member == "class_member_val"
    assert inst_dep_obj.x == "x_val"

    assert "ClassDependency" in agent_comp.dependencies.keys()
    class_dep_obj = agent_comp.dependencies["ClassDependency"].get_object()
    assert type(class_dep_obj) == type
    assert class_dep_obj.class_member == "class_member_val"
    assert not hasattr(class_dep_obj, "x")
    assert class_dep_obj().x == "x_val"

    # Instantiate a SimpleAgent and run reset_env() method
    r = agent_comp.run_with_arg_set("reset_env")
    assert type(r) == ComponentRun
    assert type(r.run_command) == RunCommand
    assert r.run_command.component == agent_comp
    assert r.run_command.entry_point == "reset_env"
    for args in r.run_command.argument_set.to_spec().values():
        assert args == {}

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
                "https://github.com/agentos-project/agentos",
                "test_freezing_version",
            )
            mocks[
                "get_prefixed_path_from_repo_root"
            ].return_value = "freeze/test.py"
            reg = c.to_frozen_registry()
            agent_spec = reg.get_component_spec("agent", flatten=True)
            assert agent_spec["repo"] == "local_dir"
            assert agent_spec["version"] == "test_freezing_version"


def test_component_from_github_with_venv():
    with auto_revert_venv():
        random_url = (
            "https://github.com/agentos-project/agentos/"
            "blob/439b705c15f499f0017b49ffea4d33afa0f7a7a5/"
            "example_agents/random/components.yaml"
        )
        random_component = Component.from_github_registry(
            random_url, "agent", use_venv=True
        )
        random_component.run_with_arg_set("run_episodes")


def test_component_from_github_no_venv():
    with auto_revert_venv():
        sb3_url = (
            "https://github.com/agentos-project/agentos/"
            "blob/master/example_agents/sb3_agent/components.yaml"
        )
        random_component = Component.from_github_registry(
            sb3_url, "sb3_agent", use_venv=False
        )
        random_component.run_with_arg_set("evaluate")


def test_module_component_from_agentos_github_repo():
    repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    c_suff = f"=={TESTING_BRANCH_NAME}"
    f_pref = "example_agents/random/"
    ag_c = Component.from_repo(repo, f"a{c_suff}", f"{f_pref}agent.py")
    env_c = Component.from_repo(repo, f"e{c_suff}", f"{f_pref}environment.py")
    pol_c = Component.from_repo(repo, f"p{c_suff}", f"{f_pref}policy.py")
    ds_c = Component.from_repo(repo, f"d{c_suff}", f"{f_pref}dataset.py")

    ag_c.instantiate = True
    ag_c.class_name = "BasicAgent"

    env_c.instantiate = True
    env_c.class_name = "Corridor"
    ag_c.add_dependency(env_c, "environment")

    pol_c.instantiate = True
    pol_c.class_name = "RandomPolicy"
    ag_c.add_dependency(pol_c, "policy")
    pol_c.add_dependency(env_c, "environment")

    ds_c.instantiate = True
    ds_c.class_name = "BasicDataset"
    ag_c.add_dependency(ds_c, "dataset")

    ag_c.run("run_episode")
