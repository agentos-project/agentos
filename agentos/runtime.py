"""Functions and classes used by the AOS runtime."""
import os
import yaml
import click
import mlflow
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from agentos.component import Component
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
    component = Component.get_from_yaml(component_name, component_spec_file)
    component.parse_param_file(param_file)
    component.add_params_to_fn(entry_point, params)
    component.run(entry_point)


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
