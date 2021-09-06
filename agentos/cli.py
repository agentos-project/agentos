"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import agentos
from agentos import runtime
import click


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

_option_num_episodes = click.option(
    "--num-episodes",
    "-n",
    type=click.INT,
    default=1,
    help="Number of episodes to run.",
)

_option_assume_yes = click.option(
    "--assume-yes",
    "-y",
    is_flag=True,
    help="Automatically answers 'yes' to all user prompts.",
)

_option_test_every = click.option(
    "--test-every",
    "-t",
    type=click.INT,
    default=0,
    help="Number of learning episodes between performance eval.",
)

_option_test_num_episodes = click.option(
    "--test-num-episodes",
    "-p",
    type=click.INT,
    default=0,
    help="Number of episodes to run for performance eval.",
)

_option_verbose = click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Agent prints verbose logs.",
)


@agentos_cmd.command()
@_arg_component_name
@_option_agentos_dir
@_option_agent_file
@_option_assume_yes
def install(component_name, agentos_dir, agent_file, assume_yes):
    """Installs PACKAGE_NAME"""
    runtime.install_component(
        component_name, agentos_dir, agent_file, assume_yes
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
    runtime.initialize_agent_directories(dir_names, agent_name, agentos_dir)


# TODO - reimplement hz and max_iters
@agentos_cmd.command()
@_option_num_episodes
@_option_test_every
@_option_test_num_episodes
@_option_agent_file
@_option_agentos_dir
@_option_verbose
def learn(
    num_episodes,
    test_every,
    test_num_episodes,
    agent_file,
    agentos_dir,
    verbose,
):
    agentos.learn(
        num_episodes,
        test_every,
        test_num_episodes,
        agent_file,
        agentos_dir,
        verbose,
    )


# TODO - reimplement hz and max_iters
@agentos_cmd.command()
@_option_num_episodes
@_option_agent_file
@_option_agentos_dir
@_option_verbose
def run(num_episodes, agent_file, agentos_dir, verbose):
    """Run an agent by calling advance() on it until it returns True"""
    should_learn = False
    agentos.run_agent(
        num_episodes, agent_file, agentos_dir, should_learn, verbose
    )


if __name__ == "__main__":
    agentos_cmd()
