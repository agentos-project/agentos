"""Functions and classes used by the AOS runtime."""
import subprocess
import os
import sys
import yaml
import click
import mlflow
import tempfile
import shutil
from datetime import datetime
import importlib.util
from pathlib import Path
import importlib
from agentos.component import ComponentNamespace
from agentos.utils import MLFLOW_EXPERIMENT_ID


def run_component(
    component_spec_file,
    component_name,
    entry_point,
    params=None,
    param_file=None,
):
    """
    :param component_spec_file: file containing this component's specification.
    :param component_name: name of component to run.
    :param entry_point: name of function to call on component.
    :param params: dict of params for the entry point being run.
    :param param_file: YAML to load params from for entry point being run.
    """
    _log_run_info(
        component_name,
        entry_point,
        component_spec_file,
        params,
        param_file,
    )
    registry = ComponentNamespace()
    registry.parse_spec_file(component_spec_file)
    registry.parse_param_file(param_file)
    registry.add_params(component_name, entry_point, params)
    component = registry.get_component(component_name)
    component.call(entry_point)


# TODO - move into and integrate with ComponentNamespace + Component
def _log_run_info(name, entry_point, spec_file, params, param_file):
    mlflow.start_run(experiment_id=MLFLOW_EXPERIMENT_ID)
    mlflow.log_param("component_name", name)
    mlflow.log_param("entry_point", entry_point)
    mlflow.log_artifact(Path(spec_file).absolute())
    _log_data_as_artifact("cli_parameters.yaml", params)
    if param_file is not None:
        mlflow.log_artifact(Path(param_file).absolute())


def _log_data_as_artifact(name: str, data: dict):
    dir_path = Path(tempfile.mkdtemp())
    artifact_path = dir_path / name
    with open(artifact_path, "w") as file_out:
        file_out.write(yaml.safe_dump(data))
    mlflow.log_artifact(artifact_path)
    shutil.rmtree(dir_path)


def install_component(component_name, agentos_dir, agent_file, assume_yes):
    _check_path_exists(agentos_dir)
    agentos_dir = Path(agentos_dir).absolute()
    registry_entry = _get_registry_entry(component_name)
    confirmed = assume_yes or _confirm_component_installation(
        registry_entry, agentos_dir
    )
    if confirmed:
        # Blow away agent training step count
        agentos_dir.mkdir(exist_ok=True)
        release_entry = _get_release_entry(registry_entry)
        repo = _clone_component_repo(release_entry, agentos_dir)
        _checkout_release_hash(release_entry, repo)
        _update_agentos_yaml(registry_entry, release_entry, repo, agent_file)
        _install_requirements(repo, release_entry)
    else:
        raise Exception("Aborting installation...")


def initialize_agent_directories(dir_names, agent_name, agentos_dir):
    dirs = [Path(".")]
    if dir_names:
        dirs = [Path(d) for d in dir_names]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        os.makedirs(agentos_dir, exist_ok=True)
        _instantiate_template_files(d, agent_name)
        d = "current working directory" if d == Path(".") else d
        click.echo(
            f"Finished initializing AgentOS agent '{agent_name}' in {d}."
        )


################################
# Private helper functions below
################################

# Necessary because the agentos_dir will **not** exist on `agentos init`
def _check_path_exists(path):
    if not Path(path).absolute().exists():
        raise click.BadParameter(f"{path} does not exist!")


def _load_parameters(parameters_file) -> dict:
    with open(parameters_file) as file_in:
        params = yaml.full_load(file_in)
        assert isinstance(params, dict)
        return params


def _get_class_from_config_section(section):
    """Takes class_path of form "module.Class" and returns the class object."""
    module_file = Path(section["file_path"])
    assert module_file.is_file(), f"{module_file} is not a file"
    sys.path.append(str(module_file.parent))
    spec = importlib.util.spec_from_file_location(
        "TEMP_MODULE", str(module_file)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, section["class_name"])
    sys.path.pop()
    return cls


def _get_registry_entry(component_name):
    agentos_root_path = Path(__file__).parent.parent
    registry_path = agentos_root_path / "registry.yaml"
    if not registry_path.is_file():
        raise Exception(f"Could not find AgentOS registry at {registry_path}")
    with open(registry_path) as file_in:
        registry = yaml.full_load(file_in)
    if component_name not in registry:
        raise click.BadParameter(f'Cannot find component "{component_name}"')
    registry[component_name]["_name"] = component_name
    return registry[component_name]


def _confirm_component_installation(registry_entry, location):
    answer = input(
        f'ACR will install component {registry_entry["_name"]} '
        f"to {location}.  Continue? (Y/N) "
    )
    return answer.strip().lower() == "y"


def _get_release_entry(registry_entry):
    # TODO - allow specification of release
    return registry_entry["releases"][0]


def _clone_component_repo(release, location):
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


def _update_agentos_yaml(registry_entry, release_entry, repo, agent_file):
    raise NotImplementedError()


# TODO - automatically install?
def _install_requirements(repo, release_entry):
    req_path = (repo / release_entry["requirements_path"]).absolute()
    print("\nInstall component requirements with the following command:")
    print(f"\n\tpip install -r {req_path}\n")


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
                        file_header=header,
                        abs_path=d.absolute(),
                        os_sep=os.sep,
                    )
                )


_AGENT_DEF_FILE = Path("./templates/agent.py")
_ENV_DEF_FILE = Path("./templates/environment.py")
_DATASET_DEF_FILE = Path("./templates/dataset.py")
_TRAINER_DEF_FILE = Path("./templates/trainer.py")
_POLICY_DEF_FILE = Path("./templates/policy.py")
_TRACKER_DEF_FILE = Path("./templates/tracker.py")
_AGENT_YAML_FILE = Path("./templates/agentos.yaml")


_INIT_FILES = [
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _POLICY_DEF_FILE,
    _DATASET_DEF_FILE,
    _TRAINER_DEF_FILE,
    _TRACKER_DEF_FILE,
    _AGENT_YAML_FILE,
]
