"""Test suite for AgentOS Module."""
from unittest.mock import DEFAULT, patch

from agentos.cli import init
from pcs import Class, FileModule, Instance
from pcs.argument_set import ArgumentSet
from pcs.command import Command
from pcs.component import Component
from pcs.output import Output
from pcs.registry import Registry
from pcs.repo import Repo
from pcs.virtual_env import VirtualEnv
from tests.utils import (
    TESTING_BRANCH_NAME,
    TESTING_GITHUB_ACCOUNT,
    TESTING_GITHUB_REPO,
    run_in_dir,
    run_test_command,
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
        kwargs={"env": env_inst, "gen_class": gen_class, "gen_inst": gen_inst}
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
    assert (
        inst_dep_obj.__class__.__name__ == "GenericDependency"
    ), inst_dep_obj.__class__.__name__
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
    assert (
        copy._mlflow_run.to_dictionary() == output._mlflow_run.to_dictionary()
    )


def test_component_freezing(cli_runner, tmpdir):
    with run_in_dir(tmpdir):
        run_test_command(cli_runner, init)
        c = FileModule.from_registry_file("components.yaml", "agent")
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
            agent_spec = reg.get_spec(frozen_inst.identifier)
            class_id = agent_spec.get_and_extract_ident("instance_of")
            mod_id = reg.get_spec(class_id).get_and_extract_ident("module")
            repo_id = reg.get_spec(mod_id).get_and_extract_ident("repo")
            version = reg.get_spec(repo_id).body["version"]
            assert version == "test_freezing_version"


def test_component_from_github_with_venv():
    with VirtualEnv():
        random_url = (
            f"https://github.com/{TESTING_GITHUB_ACCOUNT}/"
            f"{TESTING_GITHUB_REPO}/blob/{TESTING_BRANCH_NAME}/"
            "example_agents/random/components.yaml"
        )
        random_component = FileModule.from_github_registry(random_url, "agent")
        random_component.run_with_arg_set("evaluate")


def test_module_component_from_agentos_github_repo():
    repo = Repo.from_github(
        TESTING_GITHUB_ACCOUNT, TESTING_GITHUB_REPO, TESTING_BRANCH_NAME
    )
    f_pref = "example_agents/random/"

    env_cls = Class(
        name="Corridor",
        module=FileModule.from_repo(repo, f"{f_pref}environment.py"),
    )
    ds = Instance(
        instance_of=Class(
            name="BasicDataset",
            module=FileModule.from_repo(repo, f"{f_pref}dataset.py"),
        )
    )
    pol = Instance(
        instance_of=Class(
            name="RandomPolicy",
            module=FileModule.from_repo(repo, f"{f_pref}policy.py"),
        ),
        argument_set=ArgumentSet(
            kwargs={
                "environment_cls": env_cls,
            }
        ),
    )
    run_cls = Class(
        name="BasicRun",
        module=FileModule.from_repo(repo, f"{f_pref}run.py"),
    )

    agent = Instance(
        instance_of=Class(
            name="BasicAgent",
            module=FileModule.from_repo(repo, f"{f_pref}agent.py"),
        ),
        argument_set=ArgumentSet(
            kwargs={
                "environment_cls": env_cls,
                "policy": pol,
                "dataset": ds,
                "run_cls": run_cls,
            }
        ),
    )
    agent.run("evaluate")


def test_diamond_dependencies():
    registry_dict = {
        "specs": {
            "one": {"type": "ArgumentSet", "args": ["spec:two", "spec:three"]},
            "two": {"type": "ArgumentSet", "args": ["spec:four", "I'm three"]},
            "three": {"type": "ArgumentSet", "args": ["spec:four", "I'm two"]},
            "four": {"type": "LocalRepo", "path": "."},
        }
    }
    reg = Registry.from_dict(registry_dict)
    one = Component.from_registry(reg, "one")
    assert one.args[0].args[0] is one.args[1].args[0]
