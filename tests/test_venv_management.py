import pytest
from pathlib import Path
from tests.utils import run_test_command
from tests.utils import TEST_VENV_AGENT_DIR
from agentos.cli import run
from agentos.component import Component


def test_venv_management(tmpdir):
    Component.set_environment_handling(use_venv=True)
    tmp_path = Path(tmpdir)
    env_cache_path = tmp_path / "test_requirements"
    env_cache_path.mkdir(parents=True, exist_ok=True)

    # Test cache clearing
    Component.set_env_cache_path(env_cache_path)
    touch_test = env_cache_path / "test_file.out"
    touch_test.touch()
    assert touch_test.exists()
    Component.clear_env_cache(assume_yes=True)
    assert not touch_test.exists()

    # Attempt to import a package not normally in our testing environment.
    # If the test fails here, it means AgentOS now requires one of these
    # libraries.  Update the test_venv_agent to use a different library.
    with pytest.raises(ModuleNotFoundError):
        import arrow  # noqa: F401
    with pytest.raises(ModuleNotFoundError):
        import bottle  # noqa: F401

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
    run_test_command(cmd=run, cli_args=venv_test_args, cli_kwargs=test_kwargs)
