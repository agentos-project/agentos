# Design and some code copied from MLflow's server codebase.
from agentos.agent import Agent
from flask import Flask, request, send_from_directory
import os
from subprocess import Popen, PIPE
import shlex

REL_STATIC_DIR = "static_content"

app = Flask(__name__, static_folder=REL_STATIC_DIR)
STATIC_DIR = os.path.join(app.root_path, REL_STATIC_DIR)

agent = Agent()

@app.route('/')
def home():
    return send_from_directory(STATIC_DIR, 'index.html')


# Provide a health check endpoint to ensure the application is responsive
@app.route("/health")
def health():
    return "OK", 200


@app.route('/status')
def status():
    running_flag = "" if agent.running else "not "
    return f"Agent {agent.name} is {running_flag}running.", 200


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route('/stop', methods=['POST'])
def shutdown():
    agent.stop()
    shutdown_server()
    return 'Server shutting down...'


@app.route('/static_content/<path:path>')
def serve_static_file(path):
    return send_from_directory(STATIC_DIR, path)


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


def run_agent_server(host, port, no_daemon=False, waitress_opts=None):
    """Use Waitress + Flask to run the AgentOS. Should work on Windows."""
    command = _build_waitress_command(waitress_opts, host, port)
    cmd_env = os.environ.copy()
    if no_daemon:
        child = Popen(command, env=cmd_env, universal_newlines=True,
                      stdin=PIPE, stderr=PIPE)
        exit_code = child.wait()
        if exit_code != 0:
            raise ShellCommandException("Non-zero exitcode: %s" % (exit_code))
        return exit_code
    else:
        return Popen(command, universal_newlines=True)

