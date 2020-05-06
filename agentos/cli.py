import click
import agent

@click.group()
def agentos_cmd():
    pass

@agentos_cmd.command()
#@click.option("--ui-port", default=8001, help="port to run agent web UI on")
def start():
    """Starts the agent."""
    click.echo("Starting agent")
    agent.start_agent()

@agentos_cmd.command()
def stop():
    """Stops the agent."""
    click.echo("Stoping the agent.")

if __name__ == "__main__":
    agentos_cmd()
