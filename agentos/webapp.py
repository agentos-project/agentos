"""Handle mapping between HTTP and AgentManager functionality.

AgentOS uses Flask to provide an HTTP microservice which wraps
a long running instance of the agentOS AgentManger class with
as minimal boilerplate and glue code as possible.
"""
from agentos import AgentManager
from flask import Flask

app = Flask(__name__)
agent_manager = AgentManager()


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
    running_flag = "" if agent_manager.running else "not "
    return f"AgentManager {agent_manager.name} is {running_flag}running.", 200


@app.route('/stop')
def _stop():
    agent_manager.stop()
    return 'AgentManager stopped.', 200
