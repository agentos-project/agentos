"""Functions and classes used by the AOS runtime."""
import pickle
import agentos
import shutil
import subprocess
import os
import uuid
import sys
import yaml
import click
from datetime import datetime
import importlib.util
from pathlib import Path
import configparser
import importlib
import statistics


# TODO - reimplement hz, max_iters, and threading
def run_agent(
    episodes,
    agent_file,
    package_location,
    should_learn,
    verbose,
    backup_dst=None,
):
    """Runs an agent specified by a given [agent_file]

    :param episodes: number of episodes to run the agent through
    :param agent_file: path to the agent config file
    :param package_location: location of the ACR agent installation
    :param should_learn: boolean, if True we will call policy.improve
    :param verbose: boolean, if True will print debugging data to stdout
    :param backup_dst: if specified, will print backup path to stdout

    :returns: None
    """
    all_steps = []
    agent = load_agent_from_path(agent_file, package_location, verbose)
    for i in range(episodes):
        steps = agent.rollout(should_learn)
        all_steps.append(steps)

    if all_steps:
        mean = statistics.mean(all_steps)
        median = statistics.median(all_steps)
        print()
        print(f"Benchmark results after {len(all_steps)} rollouts:")
        print(
            f"\tBenchmarked agent was trained on {agent.get_step_count()} "
            f"transitions over {agent.get_episode_count()} episodes"
        )
        print(f"\tMax steps over {episodes} trials: {max(all_steps)}")
        print(f"\tMean steps over {episodes} trials: {mean}")
        print(f"\tMedian steps over {episodes} trials: {median}")
        print(f"\tMin steps over {episodes} trials: {min(all_steps)}")
        if backup_dst:
            print(f"Agent backed up in {backup_dst}")
        print()


def install_package(package_name, package_location, agent_file, assume_yes):
    package_location = Path(package_location).absolute()
    registry_entry = _get_registry_entry(package_name)
    confirmed = assume_yes or _confirm_package_installation(
        registry_entry, package_location
    )
    if confirmed:
        # Blow away agent training step count
        _create_core_data(package_location)
        _create_package_directory_structure(package_location)
        release_entry = _get_release_entry(registry_entry)
        repo = _clone_package_repo(release_entry, package_location)
        _checkout_release_hash(release_entry, repo)
        _update_agentos_ini(registry_entry, release_entry, repo, agent_file)
        _install_requirements(repo, release_entry)
    else:
        raise Exception("Aborting installation...")


def initialize_agent_directories(dir_names, agent_name, package_location):
    dirs = [Path(".")]
    if dir_names:
        dirs = [Path(d) for d in dir_names]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        curr_package_location = d / package_location
        _create_agent_directory_structure(curr_package_location)
        _create_core_data(curr_package_location)
        _instantiate_template_files(d, agent_name)
        d = "current working directory" if d == Path(".") else d
        click.echo(
            f"Finished initializing AgentOS agent '{agent_name}' in {d}."
        )


def learn(**kwargs):
    """Trains an agent by calling its learn() method in a loop."""
    episodes = kwargs["episodes"]
    test_every = kwargs["test_every"]
    test_episodes = kwargs["test_episodes"]
    agent_file = kwargs["agent_file"]
    package_location = kwargs["package_location"]
    verbose = kwargs["verbose"]
    should_learn = False
    agent = load_agent_from_path(agent_file, package_location, verbose)

    for i in range(episodes):
        if test_every and i % test_every == 0:
            backup_dst = _back_up_agent(package_location)
            agentos.run_agent(
                test_episodes,
                agent_file,
                package_location,
                should_learn,
                verbose,
                backup_dst=backup_dst,
            )
        agent.learn()


def load_agent_from_path(agent_file, package_location, verbose):
    """Loads agent from an agent directory

    :param agent_file: path the agentos.ini config file
    :param package_location: path to agent installation directory

    :returns: Instantiated Agent class from directory
    """
    agent_path = Path(agent_file)
    agent_dir_path = agent_path.parent.absolute()
    config = configparser.ConfigParser()
    config.read(agent_path)

    _decorate_save_data_fns(package_location)

    env_cls = _get_class_from_config(agent_dir_path, config["Environment"])
    policy_cls = _get_class_from_config(agent_dir_path, config["Policy"])
    dataset_cls = _get_class_from_config(agent_dir_path, config["Dataset"])
    trainer_cls = _get_class_from_config(agent_dir_path, config["Trainer"])
    agent_cls = _get_class_from_config(agent_dir_path, config["Agent"])

    agent_kwargs = {}
    shared_data = {}
    component_cls = {
        "environment": env_cls,
        "policy": policy_cls,
        "dataset": dataset_cls,
        "trainer": trainer_cls,
    }
    while len(component_cls) > 0:
        to_initialize_name = None
        to_initialize_cls = None
        for name, cls in component_cls.items():
            if cls.ready_to_initialize(shared_data):
                to_initialize_name = name
                to_initialize_cls = cls
                break
        if to_initialize_name is None or to_initialize_cls is None:
            exc_msg = (
                "Could not find component ready to initialize.  "
                "Perhaps there is a circular dependency?  "
                f"Remaining components: {component_cls}"
            )
            raise Exception(exc_msg)

        del component_cls[to_initialize_name]
        agent_kwargs[to_initialize_name] = to_initialize_cls(
            shared_data=shared_data, **config[to_initialize_name.capitalize()]
        )

    agent_kwargs = {
        "shared_data": shared_data,
        **agent_kwargs,
        "verbose": verbose,
        **config["Agent"],
    }
    return agent_cls(**agent_kwargs)


# https://github.com/deepmind/sonnet#tensorflow-checkpointing
# TODO - custom saver/restorer functions
# TODO - V hacky way to pass in the global data location; we decorate
#        this function with the location in restore_saved_data in cli.py
# TODO - ONLY works for the demo (Acme on TF) because the dynamic module
#        loading in ACR core breaks pickle. Need to figure out a more general
#        way to handle this
def save_tensorflow(name, network):
    print("Saving module")
    import tensorflow as tf

    checkpoint = tf.train.Checkpoint(module=network)
    checkpoint.save(save_tensorflow.data_location / name)


# https://github.com/deepmind/sonnet#tensorflow-checkpointing
# Same caveats as save_tensorflow above
def restore_tensorflow(name, network):
    import tensorflow as tf

    checkpoint = tf.train.Checkpoint(module=network)
    latest = tf.train.latest_checkpoint(restore_tensorflow.data_location)
    if latest is not None:
        print("AOS: Restoring policy network from checkpoint")
        checkpoint.restore(latest)
    else:
        print("AOS: No checkpoint found for policy network")


def save_data(name, data):
    with open(save_data.data_location / name, "wb") as f:
        pickle.dump(data, f)


def restore_data(name):
    with open(restore_data.data_location / name, "rb") as f:
        return pickle.load(f)


class ParameterObject:
    pass


parameters = ParameterObject()

################################
# Private helper functions below
################################


def _back_up_agent(package_location):
    """Creates a snapshot of an agent at a given moment in time.

    :param package_location: path to agent package location

    :returns: Path to the back up directory
    """
    package_location = Path(package_location).absolute()
    data_location = _get_data_location(package_location)
    backup_dst = _get_backups_location(package_location) / str(uuid.uuid4())
    shutil.copytree(data_location, backup_dst)
    return backup_dst


def _load_parameters(parameters_file):
    if not os.path.isfile(parameters_file):
        return
    with open(parameters_file) as file_in:
        component_parameters = yaml.full_load(file_in)
    # Throw error if two components specify same param with different values
    for k, v in component_parameters.items():
        if k in agentos.parameters.__dict__:
            if v != agentos.parameters.__dict__[k]:
                raise Exception(f"Unharmonized global setting {k}:{v}")
        agentos.parameters.__dict__[k] = v


def _get_class_from_config(agent_dir_path, config):
    """Takes class_path of form "module.Class" and returns the class object."""
    sys.path.append(config["python_path"])
    file_path = agent_dir_path / Path(config["file_path"])
    spec = importlib.util.spec_from_file_location("TEMP_MODULE", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, config["class_name"])
    _load_parameters(Path(config["python_path"]) / "parameters.yaml")
    sys.path.pop()
    return cls


# TODO - V hacky!  is this the a reasonable way to go?
# TODO - uglily communicates to save_data() the dynamic data location
def _decorate_save_data_fns(package_location):
    dl = _get_data_location(package_location)
    save_data.__dict__["data_location"] = dl
    restore_data.__dict__["data_location"] = dl
    save_tensorflow.__dict__["data_location"] = dl
    restore_tensorflow.__dict__["data_location"] = dl


def _get_registry_entry(package_name):
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


def _confirm_package_installation(registry_entry, location):
    answer = input(
        f'ACR will install component {registry_entry["_name"]} '
        f"to {location}.  Continue? (Y/N) "
    )
    return answer.strip().lower() == "y"


def _create_package_directory_structure(package_location):
    os.makedirs(package_location, exist_ok=True)


def _get_release_entry(registry_entry):
    # TODO - allow specification of release
    return registry_entry["releases"][0]


def _clone_package_repo(release, location):
    repo_name = release["github_url"].split("/")[-1]
    clone_destination = (Path(location) / repo_name).absolute()
    if clone_destination.exists():
        raise click.BadParameter(f"{clone_destination} already exists!")
    cmd = ["git", "clone", release["github_url"], clone_destination]
    result = subprocess.run(cmd)
    assert result.returncode == 0, "Git returned non-zero on repo checkout"
    assert clone_destination.exists(), f"Unable to clone repo {repo_name}"
    return clone_destination


def _checkout_release_hash(release, repo):
    curr_dir = os.getcwd()
    os.chdir(repo)
    git_hash = release["hash"]
    cmd = ["git", "checkout", "-q", git_hash]
    result = subprocess.run(cmd)
    assert result.returncode == 0, f"FAILED: checkout {git_hash} in {repo}"
    os.chdir(curr_dir)


def _update_agentos_ini(registry_entry, release_entry, repo, agent_file):
    print(repo)
    config = configparser.ConfigParser()
    config.read(agent_file)
    if registry_entry["type"] == "environment":
        section = "Environment"
    elif registry_entry["type"] == "policy":
        section = "Policy"
    elif registry_entry["type"] == "dataset":
        section = "Dataset"
    elif registry_entry["type"] == "trainer":
        section = "Trainer"
    else:
        raise Exception(f"Component component type: {registry_entry['type']}")

    # TODO - allow multiple components of same type installed
    if section in config:
        print(
            f"Replacing current environment {dict(config[section])} "
            f'with {registry_entry["_name"]}'
        )
    module_path = Path(repo).absolute()
    file_path = (module_path / release_entry["file_path"]).absolute()
    config[section]["file_path"] = str(file_path)
    config[section]["class_name"] = release_entry["class_name"]
    config[section]["python_path"] = str(module_path)
    with open(agent_file, "w") as out_file:
        config.write(out_file)


# TODO - automatically install?
def _install_requirements(repo, release_entry):
    req_path = (repo / release_entry["requirements_path"]).absolute()
    print("\nInstall component requirements with the following command:")
    print(f"\n\tpip install -r {req_path}\n")


def _create_agent_directory_structure(package_location):
    os.makedirs(package_location, exist_ok=True)
    os.makedirs(_get_data_location(package_location), exist_ok=True)
    os.makedirs(_get_backups_location(package_location), exist_ok=True)


def _create_core_data(package_location):
    _decorate_save_data_fns(package_location)
    agentos.save_data("step_count", 0)
    agentos.save_data("episode_count", 0)


def _instantiate_template_files(d, agent_name):
    AOS_PATH = Path(__file__).parent
    for file_path in _INIT_FILES:
        with open(AOS_PATH / file_path, "r") as fin:
            with open(d / file_path.name, "w") as fout:
                print(file_path)
                content = fin.read()
                now = datetime.now().strftime("%b %d, %Y %H:%M:%S")
                header = (
                    "# This file was auto-generated by `agentos init` "
                    f"on {now}."
                )
                fout.write(
                    content.format(
                        agent_name=agent_name,
                        conda_env=_CONDA_ENV_FILE.name,
                        file_header=header,
                        abs_path=d.absolute(),
                        os_sep=os.sep,
                    )
                )


_CONDA_ENV_FILE = Path("./templates/conda_env.yaml")
_MLFLOW_PROJECT_FILE = Path("./templates/MLProject")
_AGENT_DEF_FILE = Path("./templates/agent.py")
_ENV_DEF_FILE = Path("./templates/environment.py")
_DATASET_DEF_FILE = Path("./templates/dataset.py")
_TRAINER_DEF_FILE = Path("./templates/trainer.py")
_POLICY_DEF_FILE = Path("./templates/policy.py")
_AGENT_INI_FILE = Path("./templates/agentos.ini")


def _get_data_location(package_location):
    return Path(package_location).absolute() / "data"


def _get_backups_location(package_location):
    return Path(package_location).absolute() / "backups"


_INIT_FILES = [
    _CONDA_ENV_FILE,
    _MLFLOW_PROJECT_FILE,
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _POLICY_DEF_FILE,
    _DATASET_DEF_FILE,
    _TRAINER_DEF_FILE,
    _AGENT_INI_FILE,
]
