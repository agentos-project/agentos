import sys
from pathlib import Path

import pytest

from agentos.cli import run
from agentos.component import Component
from agentos.repo import LocalRepo, Repo
from agentos.specs import RepoSpecKeys
from agentos.virtual_env import VirtualEnv, auto_revert_venv
from tests.utils import RANDOM_AGENT_DIR, TEST_VENV_AGENT_DIR, run_test_command


def _clean_up_sys_modules():
    if "arrow" in sys.modules:
        del sys.modules["arrow"]
    if "bottle" in sys.modules:
        del sys.modules["bottle"]


# Attempt to import a package not normally in our testing environment.
# If the test fails here, it means AgentOS now requires one of these
# libraries.  Update the test_venv_agent to use a different library.
def _confirm_modules_not_in_env():
    with pytest.raises(ModuleNotFoundError):
        import arrow  # noqa: F401
    with pytest.raises(ModuleNotFoundError):
        import bottle  # noqa: F401


def test_venv_management(tmpdir):
    with auto_revert_venv():
        _clean_up_sys_modules()
        _confirm_modules_not_in_env()
        tmp_path = Path(tmpdir)
        env_cache_path = tmp_path / "test_requirements"
        env_cache_path.mkdir(parents=True, exist_ok=True)

        # Test cache clearing
        touch_test = env_cache_path / "test_file.out"
        touch_test.touch()
        assert touch_test.exists()
        VirtualEnv.clear_env_cache(
            env_cache_path=env_cache_path, assume_yes=True
        )
        Repo.clear_repo_cache(repo_cache_path=env_cache_path, assume_yes=True)
        assert not touch_test.exists()

        # Should fail because of --no_venv
        no_venv_test_args = ["test_venv_agent", "--use-outer-env"]
        test_kwargs = {
            "--registry-file": str(TEST_VENV_AGENT_DIR / "components.yaml")
        }
        with pytest.raises(ModuleNotFoundError):
            run_test_command(
                cmd=run, cli_args=no_venv_test_args, cli_kwargs=test_kwargs
            )

        # Should succeed because we will create a venv
        venv_test_args = ["test_venv_agent"]
        run_test_command(
            cmd=run, cli_args=venv_test_args, cli_kwargs=test_kwargs
        )


def test_venv_repl(tmpdir):
    with auto_revert_venv():
        _clean_up_sys_modules()
        _confirm_modules_not_in_env()
        venv_path = Path(tmpdir) / "reqs"
        venv = VirtualEnv(venv_path=venv_path)
        assert not venv_path.exists()
        venv.create_virtual_env()
        assert venv_path.exists()

        # These packages are not found in our venv either
        with venv:
            _confirm_modules_not_in_env()

        req_file = TEST_VENV_AGENT_DIR / "requirements.txt"
        venv.install_requirements_file(req_file)

        # import success
        with venv:
            import arrow  # noqa: F401 F811

        # Fail because context manager __exit__ deactivates the venv
        with pytest.raises(ModuleNotFoundError):
            import bottle  # noqa: F401 F811

        venv.activate()
        import bottle  # noqa: F401 F811

        venv.deactivate()


def test_setup_py_agent():
    with auto_revert_venv():
        _clean_up_sys_modules()
        _confirm_modules_not_in_env()
        local_repo_spec = {
            "local__setup_py_agent__repo": {
                RepoSpecKeys.TYPE: "local",
                RepoSpecKeys.PATH: "test_agents/setup_py_agent/",
            }
        }
        base_dir = Path(__file__).parent
        agent_repo = Repo.from_spec(local_repo_spec, base_dir=base_dir)
        agent_c = Component.from_repo(
            repo=agent_repo,
            identifier="BasicAgent",
            file_path="./agent.py",
            class_name="BasicAgent",
            instantiate=True,
            requirements_path="./setup.py",
        )
        agent_c.run("evaluate")


def test_only_activate_venv_once():
    with auto_revert_venv():
        _clean_up_sys_modules()
        _confirm_modules_not_in_env()
        random_agent_repo = LocalRepo(
            "random_agent_repo", local_dir=RANDOM_AGENT_DIR
        )
        print(random_agent_repo)
        random_agent_component = Component.from_repo(
            repo=random_agent_repo,
            identifier="BasicAgent",
            file_path="./agent.py",
            class_name="BasicAgent",
            instantiate=True,
            requirements_path="./requirements.txt",
        )
        random_agent_component.get_object()
        env_component_no_reqs = Component.from_repo(
            repo=random_agent_repo,
            identifier="Corridor1",
            file_path="./environment.py",
            class_name="Corridor",
            instantiate=True,
        )
        # OK to add a dependency without reqs to a Component with active venv
        random_agent_component.add_dependency(
            env_component_no_reqs, attribute_name="env1"
        )
        random_agent_component.get_object()
        env_component_reqs = Component.from_repo(
            repo=random_agent_repo,
            identifier="Corridor2",
            file_path="./environment.py",
            class_name="Corridor",
            instantiate=True,
            requirements_path="./requirements.txt",
        )
        # Should explode because venv is active and we're adding new reqs
        with pytest.raises(Exception):
            random_agent_component.add_dependency(
                env_component_reqs, attribute_name="env2"
            )
