"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import agentos
import click
import sys
from agentos import runtime


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

_arg_dir_names = click.argument("dir_names", nargs=-1, metavar="DIR_NAMES")

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

_option_agent_file = click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agentos.ini",
    help="Path to agent definition file (agentos.ini).",
)

_option_assume_yes = click.option(
    "--assume-yes",
    "-y",
    is_flag=True,
    help="Automatically answers 'yes' to all user prompts.",
)


@agentos_cmd.command()
@_arg_component_name
@_option_agent_file
@_option_agentos_dir
@_option_assume_yes
def install(component_name, agent_file, agentos_dir, assume_yes):
    """Installs PACKAGE_NAME"""
    runtime.install_component(
        component_name=component_name,
        agentos_dir=agentos_dir,
        agent_file=agent_file,
        assume_yes=assume_yes,
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
    runtime.initialize_agent_directories(
        dir_names=dir_names, agent_name=agent_name, agentos_dir=agentos_dir
    )


@agentos_cmd.command()
@_arg_component_name
@click.option(
    "--component-spec-file",
    "-s",
    type=click.Path(exists=True),
    default="./agentos.ini",
    help="Path to component spec file (agentos.ini).",
)
@click.option(
    "--entry-point",
    metavar="ENTRY_POINT",
    type=str,
    default="evaluate",
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
    component_name, component_spec_file, entry_point, param_list, param_file,
):
    param_dict = _user_args_to_dict(param_list)
    agentos.run_component(
        component_spec_file,
        component_name,
        entry_point,
        param_dict,
        param_file,
    )


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


if __name__ == "__main__":
    agentos_cmd()
