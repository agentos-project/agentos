"""AgentOS Server RESTfully hosts an AgentManager."""
from agentos import AgentManager
from flask import Flask
from importlib import import_module
from pathlib import Path
import os
from subprocess import Popen, PIPE
import shlex
import yaml

app = Flask(__name__)
agent = AgentManager()


@app.route('/')
def _home():
    home_content = \
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>AgentOS Hompage</title>
        </head>
        <body>
            <p>Your agentOS is running!</p>
        </body>
        </html>
        """
    return home_content, 200


# Provide a health check endpoint to ensure the application is responsive
@app.route("/health")
def _health():
    return "OK", 200


@app.route('/status')
def _status():
    running_flag = "" if agent.running else "not "
    return f"AgentManager {agent.name} is {running_flag}running.", 200


@app.route('/stop')
def _stop():
    agent.stop()
    return 'AgentManager stopped.', 200


# Copied from MLflow
def _build_waitress_command(waitress_opts, host, port):
    opts = shlex.split(waitress_opts) if waitress_opts else []
    return ['waitress-serve'] + \
           opts + [
               "--host=%s" % host,
               "--port=%s" % port,
               "--ident=agentos",
               "agentos.server:app"
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


