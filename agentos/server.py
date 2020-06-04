"""AgentOS Server runs an agent as a background process

This agentos.server modules provides an API for starting,
stopping, and interacting with an AgentOS Server.
"""
import click
import os
from pathlib import Path
import requests
from subprocess import Popen, PIPE
import shlex
import yaml

DOT_DIR = Path("./.agentos")
AGENT_MGR_INSTANCES = DOT_DIR / "agent_mgr_instances.yaml"
AGENT_MGR_CONTENT = \
    """{file_header}
    # Each time a new instance of this AgentManager is created by AgentOS (e.g., via
    # the agentos CLI) using this AgentManager Directory, information about 
    # the AgentManager process, including its PID is appended below. If there are
    # no lines below, no AgentManager Instance has been successfully been started 
    # out of this AgentManager Directory.
    
    """
BUILDFILE_FILE = "agentos_buildfile.yaml"
BUILDFILE_CONTENT = \
    """{file_header}
    # Use this file to Add agents and environments to your AgentOS.
    # See the AgentOS documentation for details.
    # For example, to add a simple agent, uncomment the following:
    #
    # env create:
    #   name: cartpole
    #   package-module: gym.envs.classic_control
    #   class: CartPoleEnv
    # 
    # agent create:
    #   package-module: agentos.agents
    #   class: RandomAgent
    #   env-name: cartpole

    """
CONDA_ENV_FILE = Path("./conda_env.yaml")
CONDA_ENV_CONTENT = \
    """{file_header}
    
    name: {name}
    
    dependencies
        - pip
        - pip: 
          - agentos
    """
MLFLOW_PROJECT_FILE = Path("./MLProject")
MLFLOW_PROJECT_CONTENT = \
    """{file_header}
    
    name: {name}
    
    conda_env: {conda_env}
    
    entry_points:
      main:
        command: "agentos start"
    """
ALL_AGENT_FILES = {AGENT_MGR_INSTANCES: AGENT_MGR_CONTENT,
                   CONDA_ENV_FILE: CONDA_ENV_CONTENT,
                   MLFLOW_PROJECT_FILE: MLFLOW_PROJECT_CONTENT}


# Copied from MLflow
def _build_waitress_command(waitress_opts, host, port):
    opts = shlex.split(waitress_opts) if waitress_opts else []
    return ['waitress-serve'] + \
           opts + [
               "--host=%s" % host,
               "--port=%s" % port,
               "--ident=agentos",
               "agentos.webapp:app"
           ]


# Copied from MLflow
class ShellCommandException(Exception):
    pass


def start(host='100.0.0.1', port=8002, daemon=True, waitress_opts=None):
    """Use Waitress + Flask to run the AgentOS Server. Should work on Windows.

    If daemon=True, returns the Popen class used to launch the server.
    If daemon=False, this is a blocking call that runs till the server
    process exists and then the exit_code of the server process is returned.
    """
    command = _build_waitress_command(waitress_opts, host, port)
    cmd_env = os.environ.copy()
    if daemon:
        return Popen(command, universal_newlines=True)
    else:
        child = Popen(command, env=cmd_env, universal_newlines=True,
                      stdin=PIPE, stderr=PIPE)
        exit_code = child.wait()
        if exit_code != 0:
            raise ShellCommandException("Non-zero exitcode: %s" % (exit_code))
        return exit_code


def agent_running(host, port):
    try:
        r = requests.get(f"http://{host}:{port}/health")
        if r.status_code == 200:
            return True
    except requests.exceptions.ConnectionError:
        pass
    return False


def get_agent_info(warn_if_none=True):
    """Return info dict about most recent agent proc if it exists, else None."""
    try:
        with open(AGENT_MGR_INSTANCES, "r") as f:
            agent_infos = yaml.safe_load(f.read())
            if agent_infos and len(agent_infos) > 0:
                return agent_infos[-1]
            if warn_if_none:
                click.echo("No AgentManager instance history entries found in "
                           f"{AGENT_MGR_INSTANCES}. Perhaps this AgentOS "
                           "Server was never started, or perhaps the "
                           f"{AGENT_MGR_INSTANCES} was edited manually?")
            return None
    except FileNotFoundError:
        if warn_if_none:
            click.echo("No agent manager history found in "
                       f"{AGENT_MGR_INSTANCES}. Perhaps agent "
                       "was never started, or that file was edited.")


def apply_buildfile(buildfile):
    print(f"Server applying {buildfile}.")
    path = Path(buildfile)
    if not path.is_file():
        print(f"Specified buildfile {buildfile} does not exist "
              "or is not of type file. Please check the file "
              "contents/location and then try again.")
        return
    if not path.read_text():
        print(f"Specified buildfile {buildfile} is empty.")
        return
    with open(buildfile, "r") as f:
        build = yaml.safe_load(f.read())
        if build and len(build) > 0:
            for operation in build:
                assert 'class' in operation.keys()
                cls = import_module(operation['class'])
                print(cls())
                print(f"applying operation {operation}")

