"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import os
from ast import literal_eval
from datetime import datetime
from pathlib import Path

import click
import yaml

from agentos.agent_run import AgentRun
from pcs.argument_set import ArgumentSet
from pcs.component import Component
from pcs.mlflow_run import MLflowRun
from pcs.module_manager import Module
from pcs.output import Output
from pcs.registry import InMemoryRegistry, Registry
from pcs.repo import Repo
from pcs.virtual_env import ManagedVirtualEnv


@click.group()
@click.version_option()
def agentos_cmd():
    pass


def _validate_agent_name(ctx, param, value):
    if " " in value or ":" in value or "/" in value:
        raise click.BadParameter("name may not contain ' ', ':', or '/'.")
    return value


_arg_identifier = click.argument("identifier", metavar="IDENTIFIER")
_arg_optional_identifier = click.argument(
    "identifier", metavar="IDENTIFIER", required=False
)
_arg_dir_names = click.argument("dir_names", nargs=-1, metavar="DIR_NAMES")
_option_registry_file = click.option(
    "--registry-file",
    "-r",
    type=click.Path(exists=True),
    multiple=True,
    default=["./components.yaml"],
    help="Path to a registry yaml file (defaults to ./components.yaml).",
)
_option_registry_string = click.option(
    "--registry-string",
    metavar="REGISTRY_STRING",
    default=None,
    help="a Python dict that is a valid pcs.Registry.",
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
_option_output_file = click.option(
    "--output-file",
    "-o",
    metavar="OUTPUT_FILE",
    default=None,
    help="Write the output to a file.",
)


@agentos_cmd.command()
@_arg_dir_names
def init(dir_names):
    """Initialize current (or specified) directory as an AgentOS agent.

    \b
    Arguments:
        [OPTIONAL] DIR_NAMES zero or more space separated directories to
                             initialize. They will be created if they do
                             not exist.

    """
    dirs = [Path(".")]
    if dir_names:
        dirs = [Path(d) for d in dir_names]

    CWD_STR = "current working directory"

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        _instantiate_template_files(d)
        d = CWD_STR if d == Path(".") else d
        click.echo(f"\nFinished initializing AgentOS agent in {d}.\n")
        click.echo("To run agent:")

        registry_path = ""
        if d != CWD_STR:
            registry_path = f"-r {d}/components.yaml"
        run_cmd = f"\tagentos run agent {registry_path}\n"
        click.echo(run_cmd)


@agentos_cmd.command()
@_arg_identifier
@click.option(
    "--function-name",
    metavar="FUNCTION_NAME",
    type=str,
    default=None,
    help="A function of the component that AgentOS Runtime will call with "
    "the specified argument set.",
)
@click.option(
    "--arg-set-id",
    "-I",
    metavar="ARG_SET_ID",
    type=str,
    default=None,
    help="The Identifier of an ArgumentSet Spec to use for this run. "
    "If None is provided, then the empty ArgumentSet will be used.",
)
@click.option(
    "--arg-set-args",
    "-A",
    metavar="ARG_SET_ARGS_STRING",
    type=str,
    default=None,
    help="a string in Python list format that contains args.",
)
@click.option(
    "--arg-set-kwargs",
    "-K",
    metavar="ARG_SET_KWARGS_STRING",
    type=str,
    default=None,
    help="a string in Python dict format that contains keyword args.",
)
@_option_registry_file
@_option_registry_string
@click.option(
    "--log-return-value/--no-log-return-value",
    metavar="LOG_RETURN_VALUE",
    type=bool,
    default=True,
    help="Whether to log the return value of the function being called.",
)
def run(
    identifier,
    function_name,
    arg_set_args,
    arg_set_kwargs,
    arg_set_id,
    registry_file,
    registry_string,
    log_return_value,
):
    if len(registry_file) == 0:
        registry = InMemoryRegistry()
    elif len(registry_file) == 1:
        registry = Registry.from_yaml(registry_file[0])
    elif len(registry_file) > 1:
        registry = Registry.from_yamls(registry_file)
    if registry_string:
        registry.update(Registry.from_dict(literal_eval(registry_string)))
    from pcs.component import Component

    comp = Component.from_registry(registry, identifier)
    function_name = function_name or comp.get_default_function_name()
    if arg_set_id:
        arg_set = ArgumentSet.from_registry(registry, arg_set_id)
    else:
        arg_set = ArgumentSet()
    args = literal_eval(arg_set_args.lstrip()) if arg_set_args else None
    kwargs = literal_eval(arg_set_kwargs.lstrip()) if arg_set_kwargs else None
    if args is not None:
        arg_set.args = arg_set.args + [args]
    if kwargs is not None:
        updated_args = arg_set.kwargs
        updated_args.update(kwargs)
        arg_set.kwargs = updated_args

    output = comp.run_with_arg_set(
        function_name, arg_set=arg_set, log_return_value=log_return_value
    )
    children = output.get_child_mlflow_runs()
    print()
    print("Output recorded.")
    print(f"\tPCS Identifier: {output.identifier}")
    print(f"\tMLflow Run ID: {output.info['run_id']}")
    print(f"\t\tagentos publish {output.info['run_id']}")
    print(f"\t\tdetails: agentos status {output.info['run_id']}")
    if children:
        print()
        print(
            f"Output with PCS Identifier {output.identifier} has the "
            f"following child MLflow Runs:"
        )
        print()
        for child in children:
            if child.data.tags.get(AgentRun.IS_AGENT_RUN_TAG):
                print(f"\tAgentRun {child.info.run_id}")
            else:
                print(f"\tOutput {child.info.run_id}")
            print(f"\t\tpublish: agentos publish {child.info.run_id}")
            print(f"\t\tdetails: agentos status {child.info.run_id}")
        print()


@agentos_cmd.command()
@_arg_optional_identifier
@_option_registry_file
def status(identifier, registry_file):
    """
    ENTITY_ID can be a Component ID or an MLflow Run ID.
    """
    print(f"identifier is {identifier}")
    if not identifier:
        MLflowRun.print_all_status()
    elif MLflowRun.run_exists(identifier):
        MLflowRun.from_existing_mlflow_run(identifier).print_status(
            detailed=True
        )
    else:  # assume identifier is a Component identifier
        try:
            registry = InMemoryRegistry()
            for reg in registry_file:
                registry.update(Registry.from_yaml(reg))
            c = Component.from_registry(registry, identifier)
            c.print_status_tree()
        except LookupError:
            print(f"No Run or component found with Identifier {identifier}.")


@agentos_cmd.command()
@_arg_identifier
def rerun(identifier):
    MLflowRun.from_registry(Registry.get_default(), identifier).rerun()


@agentos_cmd.command()
@_arg_identifier
@_option_registry_file
@_option_force
@_option_output_file
def freeze(identifier, registry_file, force, output_file):
    """
    Creates a version of ``registry_file`` for Module
    ``identifier`` where all Components in the dependency tree are
    associated with a specific git commit.  The resulting
    ``registry_file`` can be run on any machine with AgentOS installed.

    The requirements for pinning a Module spec are as follows:
        * All Components in the dependency tree must be in git repos
        * Those git repos must have GitHub as their origin
        * The current local branch and its counterpart on origin are at
          the same commit
        * There are no uncommitted changes in the local repo
    """
    registry = InMemoryRegistry()
    for reg in registry_file:
        registry.update(Registry.from_yaml(reg))
    module = Module.from_registry(registry, identifier)
    frozen_reg = module.freeze(force=force).to_registry()
    if output_file:
        with open(output_file, "w") as f:
            yaml.dump(frozen_reg.to_dict(), f)
    else:
        print(yaml.dump(frozen_reg.to_dict()))


@agentos_cmd.command()
@_arg_identifier
def publish(identifier):
    # If identifier is a Run.
    r = MLflowRun.from_existing_mlflow_run(run_id=identifier)
    if AgentRun.IS_AGENT_RUN_TAG in r.data["tags"]:
        r = AgentRun.from_existing_mlflow_run(run_id=identifier)
    if Output.IS_COMPONENT_RUN_TAG in r.data["tags"]:
        r = Output.from_existing_mlflow_run(run_id=identifier)
    r.to_registry(Registry.from_default())


@agentos_cmd.command()
@_option_assume_yes
def clear_env_cache(assume_yes):
    """
    This command clears all virtual environments that have been cached by
    AgentOS in your local file system.  All the virtual environments can be
    automatically recreated when re-running a Module that has
    ``requirements_path`` specified.
    """
    ManagedVirtualEnv.clear_env_cache(assume_yes=assume_yes)


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
    ManagedVirtualEnv.clear_env_cache(assume_yes=assume_yes)
    Repo.clear_repo_cache(assume_yes=assume_yes)


def _instantiate_template_files(d):
    AOS_PATH = Path(__file__).parent
    for file_path in _INIT_FILES:
        with open(AOS_PATH / file_path) as fin:
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
                        file_header=header,
                        abs_path=d.absolute(),
                        os_sep=os.sep,
                    )
                )


_AGENT_DEF_FILE = Path("./templates/agent.py")
_ENV_DEF_FILE = Path("./templates/environment.py")
_DATASET_DEF_FILE = Path("./templates/dataset.py")
_POLICY_DEF_FILE = Path("./templates/policy.py")
_RUN_DEF_FILE = Path("./templates/run.py")
_AGENT_YAML_FILE = Path("./templates/components.yaml")
_REQUIREMENTS_FILE = Path("./templates/requirements.txt")
_README_FILE = Path("./templates/README.md")


_INIT_FILES = [
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _DATASET_DEF_FILE,
    _POLICY_DEF_FILE,
    _RUN_DEF_FILE,
    _AGENT_YAML_FILE,
    _REQUIREMENTS_FILE,
    _README_FILE,
]


if __name__ == "__main__":
    agentos_cmd()
