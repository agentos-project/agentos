import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.absolute()
EXAMPLE_AGENT_PATH = REPO_ROOT / "example_agents"
DEV_REQS_PATH = REPO_ROOT / "dev-requirements.txt"
ACME_DQN_REQS_PATH = EXAMPLE_AGENT_PATH / "acme_dqn" / "requirements.txt"
ACME_R2D2_REQS_PATH = EXAMPLE_AGENT_PATH / "acme_r2d2" / "requirements.txt"
RLLIB_REQS_PATH = EXAMPLE_AGENT_PATH / "rllib_agent" / "requirements.txt"
SB3_REQS_PATH = EXAMPLE_AGENT_PATH / "sb3_agent" / "requirements.txt"
PAPAG_REQS_PATH = EXAMPLE_AGENT_PATH / "papag" / "requirements.txt"
WEB_REQS_PATH = REPO_ROOT / "web" / "requirements.txt"

PYTORCH_CPU_URL = "https://download.pytorch.org/whl/cpu/torch_stable.html"


def install_with_pip(pip):  # install with given pip
    # Install without embedded flags to get yaml for VirtualEnv import
    _install_path(pip, DEV_REQS_PATH, get_embedded_flags=False)
    # Acme only runs on linux due to reverb requirement
    if sys.platform == "linux":
        _install_path(pip, ACME_DQN_REQS_PATH)
        _install_path(pip, ACME_R2D2_REQS_PATH)
    _install_path(pip, RLLIB_REQS_PATH)
    _install_path(pip, SB3_REQS_PATH)
    _install_path(pip, PAPAG_REQS_PATH)
    _install_path(pip, WEB_REQS_PATH)
    _install_path(pip, REPO_ROOT, editable=True, get_embedded_flags=False)


def _install_path(pip, req_path, editable=False, get_embedded_flags=True):
    install_flag = "-r"
    if editable:
        install_flag = "-e"
    cmd = [pip, "install", install_flag, req_path]
    if get_embedded_flags:
        from pcs.virtual_env import VirtualEnv

        flags = VirtualEnv()._get_embedded_pip_flags(req_path)
        for flag_name, flag_val in flags.items():
            cmd.append(flag_name)
            cmd.append(flag_val)
    _run(cmd)


def _run(cmd):
    print(f"\n==========\nRUNNING:\n\t{cmd }\n==========\n")
    subprocess.run(cmd)


def install_requirements():
    answer = "n"
    if len(sys.argv) > 1 and sys.argv[1] == "-y":
        print("-y passed; will not confirm installation")
        answer = "y"
    else:
        msg = (
            "This will install all dev requirements and example agent "
            "Python requirements into the currently active virtualenv.  "
            "Continue [y/n]? "
        )
        answer = input(msg)

    if answer.lower() not in ["y", "yes"]:
        print("Aborting...")
        sys.exit(0)

    # check if pip is installed and valid
    pip_installed = True
    try:
        subprocess.check_call(["pip", "--version"], stdout=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pip_installed = False

    # check if conda is installed and valid
    conda_installed = True
    try:
        subprocess.check_call(
            ["conda", "--version"], stdout=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError, PermissionError):
        conda_installed = False

    # On Apple Silicon, as of 3/23/22 using pip directly to install scipy and
    # grpcio is broken but conda installing them works and installs them as
    # pip packages.
    if (
        sys.platform == "darwin"
        and platform.processor() == "arm"
        and conda_installed
    ):
        _run(["conda", "install", "-y", "scipy", "grpcio"])

    if pip_installed:
        install_with_pip("pip")
    else:  # if pip is not installed, try again with pip3 before failing
        pip3_installed = True
        try:
            subprocess.check_call(
                ["pip3", "--version"], stdout=subprocess.DEVNULL
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            pip3_installed = False

        if pip3_installed:  # if pip3 exists
            install_with_pip("pip3")

    if not (pip_installed) and not (pip3_installed):
        print("No valid pip or pip3 found, aborting...")


if __name__ == "__main__":
    install_requirements()
