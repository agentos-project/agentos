import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.absolute()
EXAMPLE_AGENT_PATH = REPO_ROOT / "example_agents"
DEV_REQS_PATH = REPO_ROOT / "dev-requirements.txt"
RLLIB_REQS_PATH = EXAMPLE_AGENT_PATH / "rllib_agent" / "requirements.txt"
SB3_REQS_PATH = EXAMPLE_AGENT_PATH / "sb3_agent" / "requirements.txt"
ACME_DQN_REQS_PATH = EXAMPLE_AGENT_PATH / "acme_dqn" / "requirements.txt"
ACME_R2D2_REQS_PATH = EXAMPLE_AGENT_PATH / "acme_r2d2" / "requirements.txt"
WEB_REQS_PATH = REPO_ROOT / "web" / "requirements.txt"

PYTORCH_CPU_URL = "https://download.pytorch.org/whl/cpu/torch_stable.html"


def install_with_pip(pip):  # install with given pip
    _run([pip, "install", "-r", DEV_REQS_PATH])
    if sys.platform == "linux":
        # Get CPU-only version of torch in case CUDA is not proper configured
        _run([pip, "install", "-r", RLLIB_REQS_PATH, "-f", PYTORCH_CPU_URL])
        _run([pip, "install", "-r", SB3_REQS_PATH, "-f", PYTORCH_CPU_URL])
        _run([pip, "install", "-r", ACME_DQN_REQS_PATH])
        _run([pip, "install", "-r", ACME_R2D2_REQS_PATH])
    else:
        _run([pip, "install", "-r", RLLIB_REQS_PATH])
        _run([pip, "install", "-r", SB3_REQS_PATH])
    _run([pip, "install", "-r", WEB_REQS_PATH])
    _run([pip, "install", "-e", REPO_ROOT])


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
