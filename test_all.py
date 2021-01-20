"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
from agentos import run_agent
from gym.envs.classic_control import CartPoleEnv
from pathlib import Path
import pytest
import subprocess
import sys


def test_random_agent():
    from agentos.agents import RandomAgent
    agent = RandomAgent(CartPoleEnv)
    done = agent.advance()
    assert not done, "CartPole never finishes after one random step."
    run_agent(RandomAgent, CartPoleEnv)


def test_cli(tmpdir):
    import subprocess
    from pathlib import Path
    subprocess.run(["agentos", "init"], cwd=tmpdir, check=True)
    main = Path(tmpdir) / "main.py"
    ml_project = Path(tmpdir) / "MLProject"
    conda_env = Path(tmpdir) / "conda_env.yaml"
    assert main.is_file()
    assert ml_project.is_file()
    assert conda_env.is_file()
    commands = [
        ["agentos", "run", "--max-iters", "5", "main.py"],
        ["agentos", "run", "--max-iters", "5", "main.py", "main.py"],
    ]
    for c in commands:
        subprocess.run(c, cwd=tmpdir, check=True)

    # TODO(andyk): add functionality for creating a conda env
    #              automatically if an MLProject file does not
    #              exist but a main.py and requirements.txt do exist.
    # also test when main.py exists and MLProject file does not.
    #ml_project.unlink()  # delete MLProject file.
    #p = subprocess.Popen(["agentos", "run"], cwd=tmpdir)
    #p.wait()
    #assert p.returncode == 0


    #TODO(andyk): add tests for all example_agents so that we keep
    #             them all working as we update the core APIs.

@pytest.mark.skip(
    reason="Version of Ray we currently use (ray[rllib]==0.8.5) requires "
           "manual build for windows."
)


######################
# Example Agent Tests
######################

def test_rllib_agent():
    import mlflow
    mlflow.run("example_agents/rllib_agent")


def test_chatbot(capsys):
    import sys
    import time
    sys.path.append("example_agents/chatbot")
    from example_agents.chatbot.main import ChatBot
    from example_agents.chatbot.env import MultiChatEnv
    env_generator = MultiChatEnv()
    # say something in the room for the agent to hear
    client_env = env_generator()
    client_env.reset()
    running_agent = run_agent(ChatBot,
                              env_generator,
                              hz=100,
                              max_iters=40,
                              as_thread=True)
    while not running_agent.is_alive():
        pass
    time.sleep(0.1)
    response_txt, _, _, _ = client_env.step("one")
    time.sleep(0.1)
    response_txt, _, _, _ = client_env.step("two")
    assert response_txt == "one", "chatbot should repeat strings from memory"
    #TODO(andyk): also test CommandLineListener


class VirtualEnvContext:
    def __init__(self, agent_dir, virtualenv, req_file="requirements.txt"):
        self.agent_dir = agent_dir
        self.virtualenv = virtualenv
        self.req_file = req_file

    def get_lib_dir(self):
        return (self.virtualenv.virtualenv / "lib").glob("python*")[0] / "site-packages"

    def __enter__(self):
        print(f"installing {self.req_file} w/ cwd {self.agent_dir}")
        self.virtualenv.run(
            ["pip", "install", "-r", self.req_file],
            cwd=Path(self.agent_dir),
            capture=True
        )
        print("sys.path is: ")
        print(sys.path)
        sys.path.insert(0, str(self.get_lib_dir()))
        print("sys.path post expansion is: ")
        print(sys.path)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type:
            return False
        #sys.path.remove(str(self.get_lib_dir()))
        #print("sys.path post reset is: ")
        #print(sys.path)


def test_rl_agents(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "rl_agents"
    with VirtualEnvContext(agent_dir, virtualenv):
        from example_agents.rl_agents.reinforce_agent import ReinforceAgent
        run_agent(ReinforceAgent, CartPoleEnv, max_iters=10)
        # TODO: uncomment and fix tests below.
        #from example_agents.rl_agents.dqn_agent import DQNAgent
        #from example_agents.rl_agents.random_nn_policy_agent import RandomTFAgent
        #run_agent(DQNAgent, CartPoleEnv, max_iters=10)
        #run_agent(RandomTFAgent, CartPoleEnv, max_iters=10)


def test_predictive_coding(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "predictive_coding" / "free_energy_tutorial"
    # Run the agent via the API
    with VirtualEnvContext(agent_dir, virtualenv) as vec:
        print(str(vec.get_lib_dir()))
        import time
        #time.sleep(500)
        from example_agents.predictive_coding.free_energy_tutorial.main import Mouse, CookieSensorEnv
        run_agent(Mouse, CookieSensorEnv, max_iters=10)
    # Run the agent via the CLI
    virtualenv.run(
        ["agentos", "run", "--max-iters", "5", "main.py"],
        cwd=agent_dir,
        stderr=subprocess.STDOUT
    )

def test_evolutionary_agent(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "evolutionary_agent"
    # Run the agent via the API
    with VirtualEnvContext(agent_dir, virtualenv):
        from example_agents.evolutionary_agent.agent import EvolutionaryAgent
        run_agent(EvolutionaryAgent, CartPoleEnv, max_iters=5)
    # Run the agent via the CLI
    virtualenv.run(
        ["agentos", "run", "--max-iters", "5", "agent.py",
         "gym.envs.classic_control.CartPoleEnv"],
        cwd=agent_dir,
        stderr=subprocess.STDOUT
    )
