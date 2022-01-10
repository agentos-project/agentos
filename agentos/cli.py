"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import os
import sys
import yaml
import click
from datetime import datetime
from pathlib import Path
from agentos import Component
from agentos import ParameterSet
from agentos.run import Run
from agentos.registry import web_registry


@click.group()
@click.version_option()
def agentos_cmd():
    pass


def _validate_agent_name(ctx, param, value):
    if " " in value or ":" in value or "/" in value:
        raise click.BadParameter("name may not contain ' ', ':', or '/'.")
    return value


_arg_component_name = click.argument(
    "component_name", metavar="COMPONENT_NAME"
)

_arg_optional_entity_id = click.argument(
    "entity_id",
    metavar="ENTITY_ID",
    required=False,
)

_arg_run_id = click.argument("run_id", type=str, metavar="RUN_ID")

_arg_dir_names = click.argument("dir_names", nargs=-1, metavar="DIR_NAMES")


_option_registry_file = click.option(
    "--registry-file",
    "-r",
    type=click.Path(exists=True),
    default="./components.yaml",
    help="Path to registry file (components.yaml).",
)


_option_agent_name = click.option(
    "--agent-name",
    "-n",
    metavar="AGENT_NAME",
    default="BasicAgent",
    callback=_validate_agent_name,
    help="This is used as the name of the MLflow Project and "
    "Conda env for all *Directory Agents* being created. "
    "AGENT_NAME may not contain ' ', ':', or '/'.",
)

_option_agentos_dir = click.option(
    "--agentos-dir",
    "-d",
    metavar="AGENTOS_DIR",
    type=click.Path(),
    default="./.aos",
    help="Directory path AgentOS components and data",
)

_option_assume_yes = click.option(
    "--assume-yes",
    "-y",
    is_flag=True,
    help="Automatically answers 'yes' to all user prompts.",
)
_option_force = click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force freeze even if repo is in a bad state.",
)


@agentos_cmd.command()
@_arg_dir_names
@_option_agent_name
@_option_agentos_dir
def init(dir_names, agent_name, agentos_dir):
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
        os.makedirs(agentos_dir, exist_ok=True)
        _instantiate_template_files(d, agent_name)
        d = "current working directory" if d == Path(".") else d
        click.echo(
            f"Finished initializing AgentOS agent '{agent_name}' in {d}."
        )


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@click.option(
    "--entry-point",
    metavar="ENTRY_POINT",
    type=str,
    default=None,
    help="A function of the component that AgentOS Runtime will call with "
    "the specified params.",
)
# Copied from https://github.com/mlflow/mlflow/blob/
# ... 3958cdf9664ade34ebcf5960bee215c80efae992/mlflow/cli.py#L54
@click.option(
    "--param-list",
    "-P",
    metavar="NAME=VALUE",
    multiple=True,
    help="A parameter for the run, of the form -P name=value. All parameters "
    "will be passed to the entry_point function using a **kwargs style "
    "keyword argument https://docs.python.org/3/glossary.html#term-argument",
)
@click.option(
    "--param-file",
    metavar="PARAM_FILE",
    help="A YAML file containing parameters for the entry point being run. "
    "Will be passed to the entry_point function, along with individually "
    "specified params, via a **kwargs style keyword argument "
    "https://docs.python.org/3/glossary.html#term-argument",
)
def run(
    component_name,
    registry_file,
    entry_point,
    param_list,
    param_file,
):
    param_dict = _user_args_to_dict(param_list)
    component = Component.from_registry_file(registry_file, component_name)
    parameters = ParameterSet.from_yaml(param_file)
    entry_point = entry_point or component.get_default_entry_point()
    parameters.update(component_name, entry_point, param_dict)
    run = component.run(entry_point, parameters)
    print(f"Run {run.id} recorded.  Execute the following for details:")
    print(f"\n  agentos status {run.id}\n")


@agentos_cmd.command()
@_arg_optional_entity_id
@_option_registry_file
def status(entity_id, registry_file):
    """
    ENTITY_ID can be a Component name or a Run ID.
    """
    if Run.run_exists(entity_id):
        Run.get_by_id(run_id=entity_id).print_status(detailed=True)
    else:
        Run.print_all_status()
        if entity_id:
            component = Component.from_registry_file(registry_file, entity_id)
            component.print_status_tree()


@agentos_cmd.command()
@_arg_optional_entity_id
def publish_run(entity_id):
    if Run.run_exists(entity_id):
        run = Run.get_by_id(run_id=entity_id)
    else:
        run = Run.get_latest_publishable_run()
        if run is None:
            raise Exception("No publishable runs found")
    run.publish()


@agentos_cmd.command()
@_arg_run_id
def get_run(run_id):
    web_registry.get_run(run_id)


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@_option_force
def freeze(component_name, registry_file, force):
    """
    Creates a version of ``registry_file`` for Component
    ``component_name`` where all Components in the dependency tree are
    associated with a specific git commit.  The resulting
    ``registry_file`` can be run on any machine with AgentOS installed.

    The requirements for pinning a Component spec are as follows:
        * All Components in the dependency tree must be in git repos
        * Those git repos must have GitHub as their origin
        * The current local branch and its counterpart on origin are at
          the same commit
        * There are no uncommitted changes in the local repo
    """
    component = Component.from_registry_file(registry_file, component_name)
    frozen_spec = component.to_frozen_registry(force=force).to_dict()
    print(yaml.dump(frozen_spec))


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@_option_force
def publish(component_name: str, registry_file: str, force: bool):
    """
    This command pushes the spec for component ``component_name`` (and all its
    sub-Components) to the AgentOS server.  This command will fail if any
    Component in the dependency tree cannot be frozen.
    """
    component = Component.from_registry_file(registry_file, component_name)
    frozen_spec = component.to_frozen_registry(force=force).to_dict()
    web_registry.add_component_spec(frozen_spec)


# Copied from https://github.com/mlflow/mlflow/blob/3958cdf9664ade34ebcf5960bee215c80efae992/mlflow/cli.py#L188 # noqa: E501
def _user_args_to_dict(arguments, argument_type="P"):
    user_dict = {}
    for arg in arguments:
        split = arg.split("=", maxsplit=1)
        # Docker arguments such as `t` don't require a value -> set to True if specified # noqa: E501
        if len(split) == 1 and argument_type == "A":
            name = split[0]
            value = True
        elif len(split) == 2:
            name = split[0]
            value = split[1]
        else:
            print(
                "Invalid format for -%s parameter: '%s'. "
                "Use -%s name=value." % (argument_type, arg, argument_type)
            )
            sys.exit(1)
        if name in user_dict:
            print("Repeated parameter: '%s'" % name)
            sys.exit(1)
        user_dict[name] = value
    return user_dict


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
_RUN_MANAGER_DEF_FILE = Path("./templates/run_manager.py")
_AGENT_YAML_FILE = Path("./templates/components.yaml")


_INIT_FILES = [
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _POLICY_DEF_FILE,
    _DATASET_DEF_FILE,
    _TRAINER_DEF_FILE,
    _RUN_MANAGER_DEF_FILE,
    _AGENT_YAML_FILE,
]


if __name__ == "__main__":
    agentos_cmd()
