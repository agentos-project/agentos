"""AgentOS command line interface (CLI).

The CLI allows creation of a simple template agent.
"""
import agentos
import click


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
    default="./.aos",
    help="Path to AgentOS Component Registry installation directory",
)
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agentos.ini",
    help="Path to agent definition file (agentos.ini).",
)
@click.option(
    "--assume-yes",
    "-y",
    is_flag=True,
    help="Automatically answers 'yes' to all user prompts.",
)
def install(package_name, package_location, agent_file, assume_yes):
    """Installs PACKAGE_NAME"""
    agentos.install_package(
        package_name, package_location, agent_file, assume_yes
    )


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
@click.option(
    "--package-location",
    "-l",
    metavar="PACKAGE_LOCATION",
    type=click.Path(),
    default="./.aos",
    help="Path to AgentOS Component Registry installation directory",
)
def init(dir_names, agent_name, package_location):
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
    agentos.initialize_agent_directories(
        dir_names, agent_name, package_location
    )


# TODO - reimplment hz and max_iters
@agentos_cmd.command()
@click.option(
    "--episodes",
    "-e",
    type=click.INT,
    default=1,
    help="Number of episodes to run.",
)
@click.option(
    "--test-every",
    "-t",
    type=click.INT,
    default=0,
    help="Number of learning episodes between performance eval.",
)
@click.option(
    "--test-episodes",
    "-p",
    type=click.INT,
    default=0,
    help="Number of episodes to run for performance eval.",
)
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agentos.ini",
    help="Path to agent definition file (agentos.ini).",
)
@click.option(
    "--package-location",
    "-l",
    metavar="PACKAGE_LOCATION",
    type=click.Path(),
    default="./.aos",
    help="Path to AgentOS Component Registry installation directory",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Agent prints verbose logs.",
)
def learn(**kwargs):
    agentos.learn(**kwargs)


# TODO - reimplement HZ and MaxIterations
@agentos_cmd.command()
@click.option(
    "--episodes",
    "-e",
    type=click.INT,
    default=1,
    help="Number of episodes to run.",
)
@click.option(
    "--agent-file",
    "-f",
    type=click.Path(exists=True),
    default="./agentos.ini",
    help="Path to agent definition file (agentos.ini).",
)
@click.option(
    "--package-location",
    "-l",
    metavar="PACKAGE_LOCATION",
    type=click.Path(),
    default="./.aos",
    help="Path to AgentOS Component Registry installation directory",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Agent prints verbose logs.",
)
def run(episodes, agent_file, package_location, verbose):
    """Run an agent by calling advance() on it until it returns True"""
    should_learn = False
    agentos.run_agent(
        episodes, agent_file, package_location, should_learn, verbose
    )


if __name__ == "__main__":
    agentos_cmd()
