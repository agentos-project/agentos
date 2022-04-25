import os
import sys

from click.testing import CliRunner
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
EXAMPLE_AGENT_DIR = ROOT_DIR / "example_agents"
RANDOM_AGENT_DIR = EXAMPLE_AGENT_DIR / "random"
CHATBOT_AGENT_DIR = EXAMPLE_AGENT_DIR / "chatbot"
ACME_DQN_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_dqn"
ACME_R2D2_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_r2d2"
GH_SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "gh_sb3_agent"
RLLIB_AGENT_DIR = EXAMPLE_AGENT_DIR / "rllib_agent"
PAPAG_AGENT_DIR = EXAMPLE_AGENT_DIR / "papag"
SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "sb3_agent"
TEST_VENV_AGENT_DIR = ROOT_DIR / "tests" / "test_agents" / "venv_agent"

TESTING_GITHUB_ACCOUNT = "andyk"
TESTING_GITHUB_REPO = "agentos"
TESTING_GITHUB_REPO_URL = (
    f"https://github.com/{TESTING_GITHUB_ACCOUNT}/{TESTING_GITHUB_REPO}"
)
TESTING_BRANCH_NAME = "spec_structure_revamp"


def run_test_command(cmd, cli_args=None, cli_kwargs=None):
    call_list = [a for a in (cli_args or [])]
    for param, val in (cli_kwargs or {}).items():
        call_list.append(param)
        call_list.append(val)
    runner = CliRunner()
    print(f"Running the following: {cmd.name} {call_list}")
    result = runner.invoke(cmd, call_list, catch_exceptions=False)
    if result.stdout_bytes:
        print()
        print("-" * 79)
        print(f"stdout from {cmd.name} {call_list}")
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print("\tError printing stdout")

    if result.stderr_bytes:
        print()
        print("-" * 79)
        print(f"STDERR from {cmd.name} {call_list}")
        try:
            print(result.stderr)
        except UnicodeEncodeError:
            print("\tError printing stderr")

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
