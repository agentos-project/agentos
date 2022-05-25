import sys
from pathlib import Path

import pytest

from agentos.cli import run
from pcs import Module, Class, Instance
from pcs.repo import Repo
from pcs.component import Component
from pcs.virtual_env import VirtualEnv, auto_revert_venv
from tests.utils import TEST_VENV_AGENT_DIR, run_test_command


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

        test_kwargs = {
            "--registry-file": str(TEST_VENV_AGENT_DIR / "components.yaml")
        }
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
                Component.TYPE_KEY: "LocalRepo",
                "path": f"{Path(__file__).parent}/test_agents/setup_py_agent/",
            }
        }
        agent_repo = Repo.from_spec(local_repo_spec)
        agent_instance = Instance(
            instance_of=Class(
                name="BasicAgent",
                module=Module.from_repo(
                    repo=agent_repo,
                    version=None,
                    file_path="./agent.py",
                    requirements_path="./setup.py",
                )
            )
        )
        agent_instance.run("evaluate")
