"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import agentos
import click
from agentos import runtime
from pathlib import Path


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
    default=1,
    help="Number of episodes to run for performance eval.",
)

_option_max_transitions = click.option(
    "--max-transitions",
    "-m",
    type=click.INT,
    default=None,
    help="The maximium number of transitions before truncating an episode",
)
_option_verbose = click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Agent prints verbose logs.",
)


@agentos_cmd.command()
@_arg_component_name
@_option_agent_file
@_option_agentos_dir
@_option_assume_yes
def install(component_name, agent_file, agentos_dir, assume_yes):
    """Installs PACKAGE_NAME"""
    _check_path_exists(agentos_dir)
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


# TODO - reimplement hz and max_iters
@agentos_cmd.command()
@_option_num_episodes
@_option_test_every
@_option_test_num_episodes
@_option_agent_file
@_option_agentos_dir
@_option_max_transitions
@_option_verbose
def learn(
    num_episodes,
    test_every,
    test_num_episodes,
    agent_file,
    agentos_dir,
    max_transitions,
    verbose,
):
    _check_path_exists(agentos_dir)
    agentos.learn(
        num_episodes=num_episodes,
        test_every=test_every,
        test_num_episodes=test_num_episodes,
        agent_file=agent_file,
        agentos_dir=agentos_dir,
        max_transitions=max_transitions,
        verbose=verbose,
    )


# TODO - reimplement hz and max_iters
@agentos_cmd.command()
@_option_num_episodes
@_option_agent_file
@_option_agentos_dir
@_option_max_transitions
@_option_verbose
def run(num_episodes, agent_file, agentos_dir, max_transitions, verbose):
    """Run an agent by calling advance() on it until it returns True"""
    _check_path_exists(agentos_dir)
    agentos.run_agent(
        num_episodes=num_episodes,
        agent_file=agent_file,
        agentos_dir=agentos_dir,
        max_transitions=max_transitions,
        should_learn=False,
        verbose=verbose,
        backup_dst=None,
        print_stats=True,
    )


def _check_path_exists(path):
    if not Path(path).absolute().exists():
        raise click.BadParameter(f"{path} does not exist!")


if __name__ == "__main__":
    agentos_cmd()
