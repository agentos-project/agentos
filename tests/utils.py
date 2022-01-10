import os
import sys
from pathlib import Path
from click.testing import CliRunner
from contextlib import contextmanager

ROOT_DIR = Path(__file__).parent.parent
EXAMPLE_AGENT_DIR = ROOT_DIR / "example_agents"
RANDOM_AGENT_DIR = EXAMPLE_AGENT_DIR / "random"
CHATBOT_AGENT_DIR = EXAMPLE_AGENT_DIR / "chatbot"
ACME_DQN_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_dqn"
ACME_R2D2_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_r2d2"
GH_SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "gh_sb3_agent"
RLLIB_AGENT_DIR = EXAMPLE_AGENT_DIR / "rllib_agent"
SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "sb3_agent"


def run_test_command(cmd, component_name=None, args=None):
    component_name = component_name or ""
    call_list = [component_name]
    for param, val in (args or {}).items():
        call_list.append(param)
        call_list.append(val)
    runner = CliRunner()
    print(f"Running the following: {cmd.name} {component_name} {call_list}")
    result = runner.invoke(cmd, call_list, catch_exceptions=False)
    assert result.exit_code == 0, result.output


@contextmanager
def run_in_dir(dir_path):
    curr_dir = os.getcwd()
    os.chdir(dir_path)
    try:
        yield
    finally:
        os.chdir(curr_dir)


def is_linux():
    return "linux" in sys.platform
