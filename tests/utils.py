import sys
from pathlib import Path
from click.testing import CliRunner

ROOT_DIR = Path(__file__).parent.parent
EXAMPLE_AGENT_DIR = ROOT_DIR / "example_agents"


def run_test_command(cmd, component_name=None, args=None):
    component_name = component_name or ''
    call_list = [component_name]
    for param, val in (args or {}).items():
        call_list.append(param)
        call_list.append(val)
    runner = CliRunner()
    print(f"Running the following: {cmd.name} {component_name} {call_list}")
    result = runner.invoke(cmd, call_list, catch_exceptions=False)
    assert result.exit_code == 0, result.output


def is_linux():
    return "linux" in sys.platform
