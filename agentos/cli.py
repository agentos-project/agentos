"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml

from pcs.argument_set import ArgumentSet
from pcs.component import Component
from pcs.registry import Registry
from pcs.repo import Repo
from pcs.run import Run
from pcs.virtual_env import VirtualEnv


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

_option_use_venv = click.option(
    "--use-auto-env/--use-outer-env",
    "use_venv",
    default=True,
    help=(
        "If --use-auto-venv is passed, then AgentOS will automatically "
        "create a virtual environment under which the Component DAG "
        "will be run. If --use-outer-env is passed, AgentOS will not "
        "create a new virtual environment for the Component DAG, instead "
        "running it in the existing outer Python environment."
    ),
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

    CWD_STR = "current working directory"

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        _instantiate_template_files(d, agent_name)
        d = CWD_STR if d == Path(".") else d
        click.echo(
            f"\nFinished initializing AgentOS agent '{agent_name}' in {d}.\n"
        )
        click.echo("To run agent:")

        registry_path = ""
        if d != CWD_STR:
            registry_path = f"-r {d}/components.yaml"
        run_cmd = f"\tagentos run agent {registry_path}\n"
        click.echo(run_cmd)


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@click.option(
    "--entry-point",
    metavar="ENTRY_POINT",
    type=str,
    default=None,
    help="A function of the component that AgentOS Runtime will call with "
    "the specified argument set.",
)
# Copied from https://github.com/mlflow/mlflow/blob/
# ... 3958cdf9664ade34ebcf5960bee215c80efae992/mlflow/cli.py#L54
@click.option(
    "--arg-set-list",
    "-A",
    metavar="NAME=VALUE",
    multiple=True,
    help="A argument for the run, of the form -A name=value. All arguments "
    "will be passed to the entry_point function using a Python kwargs-style "
    "keyword argument https://docs.python.org/3/glossary.html#term-argument",
)
@click.option(
    "--arg-set-file",
    metavar="PARAM_FILE",
    help="A YAML file containing arguments for the entry point being run. "
    "Will be passed to the entry_point function, along with individually "
    "specified args, via a Python kwargs-style keyword argument "
    "https://docs.python.org/3/glossary.html#term-argument",
)
@_option_use_venv
def run(
    component_name,
    registry_file,
    entry_point,
    arg_set_list,
    arg_set_file,
    use_venv,
):
    cli_arg_dict = _user_args_to_dict(arg_set_list)
    component = Component.from_registry_file(
        registry_file, component_name, use_venv=use_venv
    )
    arg_set = ArgumentSet.from_yaml(arg_set_file)
    entry_point = entry_point or component.get_default_entry_point()
    arg_set.update(component_name, entry_point, cli_arg_dict)
    run = component.run_with_arg_set(entry_point, arg_set)
    print(f"Run {run.identifier} recorded.", end=" ")
    print("Execute the following for details:")
    print(f"\n  agentos status {run.identifier}\n")


@agentos_cmd.command()
@_arg_optional_entity_id
@_option_registry_file
@_option_use_venv
def status(entity_id, registry_file, use_venv):
    """
    ENTITY_ID can be a Component name or a Run ID.
    """
    print(f"entity_id is {entity_id}")
    if not entity_id:
        Run.print_all_status()
    elif Run.run_exists(entity_id):
        Run.from_existing_run_id(entity_id).print_status(detailed=True)
    else:  # assume entity_id is a ComponentIdentifier
        try:
            c = Component.from_registry_file(
                registry_file, entity_id, use_venv=use_venv
            )
            c.print_status_tree()
        except LookupError:
            print(f"No Run or component found with Identifier {entity_id}.")


@agentos_cmd.command()
@_arg_optional_entity_id
def publish_run(entity_id):
    Run.from_existing_run_id(run_id=entity_id).publish()


@agentos_cmd.command()
@_arg_run_id
def rerun(run_id):
    Run.from_registry(Registry.get_default(), run_id).rerun()


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@_option_force
@_option_use_venv
def freeze(component_name, registry_file, force, use_venv):
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
    component = Component.from_registry_file(
        registry_file, component_name, use_venv=use_venv
    )
    frozen_reg = component.to_frozen_registry(force=force)
    print(yaml.dump(frozen_reg.to_dict()))


@agentos_cmd.command()
@_arg_component_name
@_option_registry_file
@_option_force
@_option_use_venv
def publish(
    component_name: str, registry_file: str, force: bool, use_venv: bool
):
    """
    This command pushes the spec for component ``component_name`` (and all its
    sub-Components) to the AgentOS server.  This command will fail if any
    Component in the dependency tree cannot be frozen.
    """
    component = Component.from_registry_file(
        registry_file, component_name, use_venv=use_venv
    )
    frozen_spec = component.to_frozen_registry(force=force).to_spec()
    Registry.get_default().add_component_spec(frozen_spec)


@agentos_cmd.command()
@_option_assume_yes
def clear_env_cache(assume_yes):
    """
    This command clears all virtual environments that have been cached by
    AgentOS in your local file system.  All the virtual environments can be
    automatically recreated when re-running a Component that has
    ``requirements_path`` specified.
    """
    VirtualEnv.clear_env_cache(assume_yes=assume_yes)


@agentos_cmd.command()
@_option_assume_yes
def clear_repo_cache(assume_yes):
    """
    This command clears all git repos that have been cached by AgentOS on your
    local file system.  These repos will be recreated as you run Components
    that require them.
    """
    Repo.clear_repo_cache(assume_yes=assume_yes)


@agentos_cmd.command()
@_option_assume_yes
def clear_cache(assume_yes):
    """
    This command clears all virtual environments AND git repos that have been
    cached by AgentOS on your local file system.
    """
    VirtualEnv.clear_env_cache(assume_yes=assume_yes)
    Repo.clear_repo_cache(assume_yes=assume_yes)


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
_POLICY_DEF_FILE = Path("./templates/policy.py")
_AGENT_YAML_FILE = Path("./templates/components.yaml")
_REQUIREMENTS_FILE = Path("./templates/requirements.txt")
_README_FILE = Path("./templates/README.md")


_INIT_FILES = [
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _POLICY_DEF_FILE,
    _DATASET_DEF_FILE,
    _AGENT_YAML_FILE,
    _REQUIREMENTS_FILE,
    _README_FILE,
]


if __name__ == "__main__":
    agentos_cmd()
