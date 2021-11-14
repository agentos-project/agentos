import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
EXAMPLE_AGENT_DIR = ROOT_DIR / "example_agents"

# Agent directories
ACME_R2D2_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_r2d2"
ACME_DQN_AGENT_DIR = EXAMPLE_AGENT_DIR / "acme_dqn"
CHATBOT_AGENT_DIR = EXAMPLE_AGENT_DIR / "chatbot"
EVOLUTIONARY_AGENT_DIR = EXAMPLE_AGENT_DIR / "evolutionary_agent"
GH_SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "gh_sb3_agent"
PREDICTIVE_CODING_AGENT_DIR = (
    EXAMPLE_AGENT_DIR / "predictive_coding" / "free_energy_tutorial"
)
RL_AGENTS_DIR = EXAMPLE_AGENT_DIR / "rl_agents"
RLLIB_AGENT_DIR = EXAMPLE_AGENT_DIR / "rllib_agent"
SB3_AGENT_DIR = EXAMPLE_AGENT_DIR / "sb3_agent"


def run_component_in_dir(
    dir_name,
    venv,
    component_name,
    entry_points=None,
    entry_point_params=None,
    req_file="requirements.txt",
):
    entry_points = entry_points or ["evaluate"]
    install_requirements(dir_name, venv, req_file)
    for i, entry_point in enumerate(entry_points):
        params = ""
        if entry_point_params:
            assert len(entry_point_params) == len(entry_points), (
                "If not None, entry_point_params must has same len() "
                "as :entry_points:"
                ""
            )
            params = entry_point_params[i]

        if os.name == "nt":
            run_cmd = (
                f"{Path(venv.bin)}/activate.bat & agentos "
                f"run {component_name} --entry-point {entry_point} {params}"
            )
        else:
            run_cmd = (
                f". {Path(venv.bin)}/activate; agentos "
                f"run {component_name} --entry-point {entry_point} {params}"
            )
        print(
            f"Using CLI to run the following command: {run_cmd} with "
            f"cwd={dir_name}."
        )
        subprocess.run(run_cmd, shell=True, cwd=dir_name, check=True)


def skip_requirements_install():
    load_dotenv()
    skip_reqs = os.getenv("AGENTOS_SKIP_REQUIREMENT_INSTALL", False)
    return True if skip_reqs == "True" else False


def install_requirements(dir_name, venv, req_file):
    if not req_file:
        return
    if skip_requirements_install():
        return
    print(f"Installing {req_file} with cwd {dir_name}")
    req_cmd = [venv.python, "-m", "pip", "install", "-r", req_file]
    subprocess.run(req_cmd, cwd=dir_name, check=True)


# Run with subprocess because we installed reqs into venv
def run_code_in_venv(venv, code):
    if skip_requirements_install():
        run_cmd = f'python -c "{code}"'
    else:
        run_cmd = f"{Path(venv.bin) / 'python'} -c \"{code}\""
    print(f"Running the following command: {run_cmd}")
    subprocess.run(run_cmd, shell=True, check=True)


def is_linux():
    return "linux" in sys.platform
