"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import agentos
import subprocess
import os
import yaml
import click
from datetime import datetime
import importlib.util
from pathlib import Path
import configparser
import importlib

CONDA_ENV_FILE = Path("./conda_env.yaml")
CONDA_ENV_CONTENT = """{file_header}

name: {agent_name}

dependencies:
    - pip
    - pip:
      - gym
      - agentos
      # Or, if you want to use your local copy of agentos, then
      # update the line below and replace the line above with it.
      #- -e path/to/agentos/git/repo
"""

MLFLOW_PROJECT_FILE = Path("./MLProject")
MLFLOW_PROJECT_CONTENT = """{file_header}

name: {agent_name}

conda_env: {conda_env}

entry_points:
  main:
    command: "python main.py"
"""

AGENT_DEF_FILE = Path("./agent.py")  # Default location of agent code.
AGENT_MAIN_FILE = Path("./main.py")
AGENT_CODE = """{file_header}
import agentos


# A basic agent.
class {agent_name}(agentos.Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obs = self.environment.reset()

    def learn(self):
        print("{agent_name} is calling self.policy.improve()")
        self.policy.improve()

    def advance(self):
        print("{agent_name} is taking an action")
        next_action = self.policy.decide(
            self.obs,
            self.environment.valid_actions
        )
        self.obs, reward, done, info = self.environment.step(next_action)
        return done
"""

ENV_DEF_FILE = Path("./environment.py")
ENV_CODE = """{file_header}
import agentos


# Simulates a 1D corridor
class Corridor(agentos.Environment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.length = 5
        self.action_space = [0, 1]
        self.observation_space = [0, 1, 2, 3, 4, 5]
        self.reset()

    def step(self, action):
        assert action in self.action_space
        if action == 0:
            self.position = max(self.position - 1, 0)
        else:
            self.position = min(self.position + 1, self.length)
        return (self.position, -1, self.done, {{}})

    def reset(self):
        self.position = 0
        return self.position

    @property
    def valid_actions(self):
        return self.action_space

    @property
    def done(self):
        return self.position >= self.length
"""

POLICY_DEF_FILE = Path("./policy.py")
POLICY_CODE = """{file_header}
import agentos
import random


# A random policy
class RandomPolicy(agentos.Policy):
    def decide(self, observation, actions):
        return random.choice(actions)

    def improve(self, **kwargs):
        pass
"""

AGENT_INI_FILE = Path("./agent.ini")
AGENT_INI_CONTENT = """
[Agent]
file_path = agent.py
class_name = {agent_name}

[Environment]
file_path = environment.py
class_name = Corridor

[Policy]
file_path = policy.py
class_name = RandomPolicy
"""

INIT_FILES = {
    CONDA_ENV_FILE: CONDA_ENV_CONTENT,
    MLFLOW_PROJECT_FILE: MLFLOW_PROJECT_CONTENT,
    AGENT_DEF_FILE: AGENT_CODE,
    ENV_DEF_FILE: ENV_CODE,
    POLICY_DEF_FILE: POLICY_CODE,
    AGENT_INI_FILE: AGENT_INI_CONTENT,
}


@click.group()
@click.version_option()
def agentos_cmd():
    pass


@agentos_cmd.command()
@click.argument("package_name", metavar="PACKAGE_NAME")
@click.option(
    "--package-location",
    "-l",
    metavar="PACKAGE_LOCATION",
    type=click.Path(),
    default="./.acr",
    help="Path to AgentOS Component Registry installation directory",
)
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agent.ini",
    help="Path to agent definition file (agent.ini).",
)
def install(package_name, package_location, agent_file):
    """Installs PACKAGE_NAME"""
    package_location = Path(package_location).absolute()
    registry_entry = get_registry_entry(package_name)
    if confirm_package_installation(registry_entry, package_location):
        create_directory_structure(package_location)
        release_entry = get_release_entry(registry_entry)
        repo = clone_package_repo(release_entry, package_location)
        checkout_release_hash(release_entry, repo)
        update_agent_ini(registry_entry, release_entry, repo, agent_file)
        install_requirements(repo, release_entry)
    else:
        raise Exception("Aborting installation...")


def get_registry_entry(package_name):
    agentos_root_path = Path(__file__).parent.parent
    registry_path = agentos_root_path / "registry.yaml"
    if not registry_path.is_file():
        raise Exception(f"Could not find AgentOS registry at {registry_path}")
    with open(registry_path) as file_in:
        registry = yaml.full_load(file_in)
    if package_name not in registry:
        raise click.BadParameter(f'Cannot find package "{package_name}"')
    registry[package_name]["_name"] = package_name
    return registry[package_name]


def confirm_package_installation(registry_entry, location):
    answer = input(
        f'ACR will install component {registry_entry["_name"]} '
        f"to {location}.  Continue? (Y/N) "
    )
    return answer.strip().lower() == "y"


def create_directory_structure(location):
    os.makedirs(location, exist_ok=True)


def get_release_entry(registry_entry):
    # TODO - allow specification of release
    return registry_entry["releases"][0]


def clone_package_repo(release, location):
    repo_name = release["github_url"].split("/")[-1]
    clone_destination = (Path(location) / repo_name).absolute()
    if clone_destination.exists():
        raise click.BadParameter(f"{clone_destination} already exists!")
    cmd = ["git", "clone", release["github_url"], clone_destination]
    result = subprocess.run(cmd)
    assert result.returncode == 0, "Git returned non-zero on repo checkout"
    assert clone_destination.exists(), f"Unable to clone repo {repo_name}"
    return clone_destination


def checkout_release_hash(release, repo):
    curr_dir = os.getcwd()
    os.chdir(repo)
    git_hash = release["hash"]
    cmd = ["git", "checkout", "-q", git_hash]
    result = subprocess.run(cmd)
    assert result.returncode == 0, f"FAILED: checkout {git_hash} in {repo}"
    os.chdir(curr_dir)


def update_agent_ini(registry_entry, release_entry, repo, agent_file):
    config = configparser.ConfigParser()
    config.read(agent_file)
    if registry_entry["type"] == "environment":
        section = "Environment"
    elif registry_entry["type"] == "policy":
        section = "Policy"
    else:
        raise Exception(f"Component component type: {registry_entry['type']}")

    # TODO - allow multiple components of same type installed
    if section in config:
        print(
            f"Replacing current environment {dict(config[section])} "
            f'with {registry_entry["_name"]}'
        )

    file_path = (Path(repo) / release_entry["file_path"]).absolute()
    config[section]["file_path"] = str(file_path)
    config[section]["class_name"] = release_entry["class_name"]
    with open(agent_file, "w") as out_file:
        config.write(out_file)


# TODO - automatically install?
def install_requirements(repo, release_entry):
    req_path = (repo / release_entry["requirements_path"]).absolute()
    print("\nInstall component requirements with the following command:")
    print(f"\n\tpip install -r {req_path}\n")


def validate_agent_name(ctx, param, value):
    if " " in value or ":" in value or "/" in value:
        raise click.BadParameter("name may not contain ' ', ':', or '/'.")
    return value


@agentos_cmd.command()
@click.argument("dir_names", nargs=-1, metavar="DIR_NAMES")
@click.option(
    "--agent-name",
    "-n",
    metavar="AGENT_NAME",
    default="BasicAgent",
    callback=validate_agent_name,
    help="This is used as the name of the MLflow Project and "
    "Conda env for all *Directory Agents* being created. "
    "AGENT_NAME may not contain ' ', ':', or '/'.",
)
def init(dir_names, agent_name):
    """Initialize current (or specified) directory as an AgentOS agent.

    \b
    Arguments:
        [OPTIONAL] DIR_NAMES zero or more space separated directories to
                             initialize. They will be created if they do
                             not exist.

    Creates an agent main.py file, a conda env, and an MLflow project file
    in all directories specified, or if none are specified, then create
    the files in current directory.
    """
    dirs = [Path(".")]
    if dir_names:
        dirs = [Path(d) for d in dir_names]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        for file_path, content in INIT_FILES.items():
            f = open(d / file_path, "w")
            now = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            header = (
                f"# This file was auto-generated by `agentos init` on {now}."
            )
            f.write(
                content.format(
                    agent_name=agent_name,
                    conda_env=CONDA_ENV_FILE.name,
                    file_header=header,
                )
            )
            f.flush()

        d = "current working directory" if d == Path(".") else d
        click.echo(
            f"Finished initializing AgentOS agent '{agent_name}' in {d}."
        )


def get_class_from_config(agent_dir_path, config):
    """Takes class_path of form "module.Class" and returns the class object."""
    file_path = agent_dir_path / Path(config["file_path"])
    spec = importlib.util.spec_from_file_location("TEMP_MODULE", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, config["class_name"])


def load_agent_from_path(agent_file):
    agent_path = Path(agent_file)
    agent_dir_path = agent_path.parent.absolute()
    config = configparser.ConfigParser()
    config.read(agent_path)

    agent_cls = get_class_from_config(agent_dir_path, config["Agent"])
    env_cls = get_class_from_config(agent_dir_path, config["Environment"])
    policy_cls = get_class_from_config(agent_dir_path, config["Policy"])

    agent_kwargs = {
        "environment": env_cls(**config["Environment"]),
        "policy": policy_cls(**config["Policy"]),
        **config["Agent"],
    }
    return agent_cls(**agent_kwargs)


@agentos_cmd.command()
@click.argument("iters", type=click.INT, required=True)
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agent.ini",
    help="Path to agent definition file (agent.ini).",
)
def learn(iters, agent_file):
    """Trains an agent by calling its learn() method in a loop."""
    agent = load_agent_from_path(agent_file)
    for i in range(iters):
        agent.learn()


@agentos_cmd.command()
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agent.ini",
    help="Path to agent definition file (agent.ini).",
)
@click.option(
    "--hz",
    "-h",
    metavar="HZ",
    default=None,
    type=int,
    help="Frequency to call agent.advance().",
)
@click.option(
    "--max-iters",
    "-m",
    metavar="MAX_STEPS",
    type=int,
    default=None,
    help="Stop running agent after this many calls to advance().",
)
def run(agent_file, hz, max_iters):
    """Run an agent by calling advance() on it until it returns True"""
    agent = load_agent_from_path(agent_file)
    agentos.run_agent(agent, hz=hz, max_iters=max_iters)


if __name__ == "__main__":
    agentos_cmd()
