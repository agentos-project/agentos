"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""

from pathlib import Path
import pytest
import subprocess

def test_random_agent():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv
    agent = RandomAgent(CartPoleEnv)
    done = agent.advance()
    assert not done, "CartPole never finishes after one random step."

    from agentos import run_agent
    run_agent(RandomAgent, CartPoleEnv)


def test_cli(tmpdir):
    import subprocess
    from pathlib import Path
    subprocess.Popen(["agentos", "init"], cwd=tmpdir).wait()
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
        p = subprocess.Popen(c, cwd=tmpdir)
        p.wait()
        assert p.returncode == 0, p.communicate()

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
    from agentos import run_agent
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


def setup_agent_test(
        agent_dir,
        virtualenv,
        req_file="requirements.txt"):
    virtualenv.run(
        ["pip", "install", "-r", req_file],
        cwd=Path(agent_dir),
        shell=True,
        capture=True
    )


def test_rl_agents(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "rl_agents"
    setup_agent_test(agent_dir, virtualenv)
    from agentos import run_agent
    from example_agents.rl_agents.reinforce_agent import ReinforceAgent
    from gym.envs.classic_control import CartPoleEnv
    run_agent(ReinforceAgent, CartPoleEnv, max_iters=10)
    # TODO: uncomment and fix tests below.
    #from example_agents.rl_agents.dqn_agent import DQNAgent
    #from example_agents.rl_agents.random_nn_policy_agent import RandomTFAgent
    #run_agent(DQNAgent, CartPoleEnv, max_iters=10)
    #run_agent(RandomTFAgent, CartPoleEnv, max_iters=10)


def test_predictive_coding(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "predictive_coding" / "free_energy_tutorial"
    setup_agent_test(agent_dir, virtualenv)
    from agentos import run_agent
    from example_agents.predictive_coding.free_energy_tutorial.main import Mouse, CookieSensorEnv
    run_agent(Mouse, CookieSensorEnv, num_steps=10)


def test_evolutionary_agent(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "evolutionary_agent"
    setup_agent_test(agent_dir, virtualenv)
    virtualenv.run(
        ["agentos", "run", "--max-iters", "5", "agent.py",
         "gym.envs.classic_control.CartPoleEnv"],
        cwd=agent_dir
    )
