"""Test suite for AgentOS Module."""
from unittest.mock import DEFAULT, patch

import pytest
from utils import run_in_dir, run_test_command

from agentos.cli import init
from pcs.argument_set import ArgumentSet
from pcs.component import Module, Class, Instance
from pcs.component_run import Output
from pcs.repo import Repo
from pcs.run_command import Command
from pcs.virtual_env import auto_revert_venv
from tests.utils import (
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
)


# We define these classes at the module global level so that
# we can create components from them. Components cannot be
# created from classes that are defined within a function.
class SimpleAgent:
    def __init__(self, env, gen_class, gen_inst):
        self.env = env
        self.gen_class = gen_class
        self.gen_inst = gen_inst

    def reset_env(self):
        self.env.reset()

    def do_something(self, z):
        return self.gen_inst.do_something(z)


class SimpleEnvironment:
    def reset(self):
        print("SimpleEnvironment.reset() called")


class GenericDependency:
    x = 1

    def __init__(self):
        self.y = 10

    def do_something(self, z):
        return self.x + self.y + z


def test_component_repl_demo():
    # Generate Components from Classes
    environment_comp = Class.from_class(SimpleEnvironment)
    env_inst = Instance(environment_comp)
    agent_class = Class.from_class(SimpleAgent)
    gen_class = Class.from_class(GenericDependency)
    gen_inst = Instance(gen_class)
    inst_args = ArgumentSet(
        kwargs={
            "env": env_inst, "gen_class": gen_class, "gen_inst": gen_inst
        }
    )
    agent_inst = Instance(instance_of=agent_class, argument_set=inst_args)

    assert "gen_class" in agent_inst.argument_set.kwargs.keys()
    class_dep_obj = agent_inst.get_object().gen_class
    assert type(class_dep_obj) == type
    assert class_dep_obj.x == 1
    assert not hasattr(class_dep_obj, "y")
    assert class_dep_obj().y == 10

    assert "gen_inst" in agent_inst.argument_set.kwargs.keys()
    agent = agent_inst.get_object()
    inst_dep_obj = agent.gen_inst
    assert inst_dep_obj.__class__.__name__ == "GenericDependency", (
        inst_dep_obj.__class__.__name__
    )
    assert inst_dep_obj.x == 1
    assert inst_dep_obj.y == 10

    # run simpleagent's reset_env() method.
    output = agent_inst.run_with_arg_set("reset_env")
    assert type(output) == Output
    assert type(output.command) == Command
    assert output.command.component == agent_inst
    assert output.command.function_name == "reset_env"

    # run gen_class's v() method, which has a return value.
    output2 = agent_inst.run_do_something(100)
    assert output2 == 111

    copy = Output.from_existing_mlflow_run(output.mlflow_run_id)
    assert copy.command == output.command
    assert copy._mlflow_run.to_dictionary() == output._mlflow_run.to_dictionary()


def test_component_freezing(tmpdir):
    with run_in_dir(tmpdir):
        run_test_command(init)
        c = Module.from_registry_file("components.yaml", "agent")
        with patch.multiple(
            "pcs.repo.Repo",
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
            frozen_inst = c.freeze()
            reg = frozen_inst.to_registry()
            agent_spec = reg.get_spec(frozen_inst.identifier, flatten=True)
            class_id = agent_spec["instance_of"]
            mod_id = reg.get_spec(class_id, flatten=True)["module"]
            version = reg.get_spec(mod_id, flatten=True)["version"]
            assert version == "test_freezing_version"


def test_component_from_github_with_venv():
    with auto_revert_venv():
        random_url = (
            f"https://github.com/{TESTING_GITHUB_ACCOUNT}/"
            f"{TESTING_GITHUB_REPO}/blob/{TESTING_BRANCH_NAME}/"
            "example_agents/random/components.yaml"
        )
        random_component = Module.from_github_registry(random_url, "agent")
        random_component.run_with_arg_set("run_episodes")


def test_component_from_github_no_venv():  # noqa: F811
    with auto_revert_venv():
        sb3_url = (
            "https://github.com/agentos-project/agentos/blob/"
            f"{TESTING_BRANCH_NAME}/example_agents/sb3_agent/components.yaml"
        )
        random_component = Module.from_github_registry(
            sb3_url, "sb3_agent", use_venv=False
        )
        random_component.run_with_arg_set("evaluate")


def test_module_component_from_agentos_github_repo():
    repo = Repo.from_github(TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO)
    c_suff = f"=={TESTING_BRANCH_NAME}"
    f_pref = "example_agents/random/"
    ag_c = Module.from_repo(repo, f"a{c_suff}", f"{f_pref}agent.py")
    env_c = Module.from_repo(repo, f"e{c_suff}", f"{f_pref}environment.py")
    pol_c = Module.from_repo(repo, f"p{c_suff}", f"{f_pref}policy.py")
    ds_c = Module.from_repo(repo, f"d{c_suff}", f"{f_pref}dataset.py")

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
