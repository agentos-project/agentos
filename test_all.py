"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
from agentos import run_agent
from pathlib import Path
import pytest


@pytest.mark.skip(reason="TODO: port example agents to new abstractions")
def test_random_agent():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv

    agent = RandomAgent(environment=CartPoleEnv())
    done = agent.advance()
    assert not done, "CartPole never finishes after one random step."
    run_agent(RandomAgent, CartPoleEnv)


def test_cli(tmpdir):
    import subprocess
    from pathlib import Path

    subprocess.run(["agentos", "init"], cwd=tmpdir, check=True)
    agent = Path(tmpdir) / "agent.py"
    environment = Path(tmpdir) / "environment.py"
    policy = Path(tmpdir) / "policy.py"
    trainer = Path(tmpdir) / "trainer.py"
    ml_project = Path(tmpdir) / "MLProject"
    conda_env = Path(tmpdir) / "conda_env.yaml"
    assert agent.is_file()
    assert environment.is_file()
    assert policy.is_file()
    assert trainer.is_file()
    assert ml_project.is_file()
    assert conda_env.is_file()
    commands = [["agentos", "train", "5"], ["agentos", "test"]]
    for c in commands:
        subprocess.run(c, cwd=tmpdir, check=True)

    # TODO(andyk): add functionality for creating a conda env
    #              automatically if an MLProject file does not
    #              exist but a main.py and requirements.txt do exist.
    # also test when main.py exists and MLProject file does not.
    # ml_project.unlink()  # delete MLProject file.
    # p = subprocess.Popen(["agentos", "run"], cwd=tmpdir)
    # p.wait()
    # assert p.returncode == 0

    # TODO(andyk): add tests for all example_agents so that we keep
    #             them all working as we update the core APIs.


######################
# Example Agent Tests
######################


@pytest.mark.skip(
    reason="Version of Ray we currently use (ray[rllib]==0.8.5) requires "
    "manual build for windows."
)
def test_rllib_agent():
    import mlflow

    mlflow.run("example_agents/rllib_agent")


@pytest.mark.skip(reason="TODO: port example agents to new abstractions")
def test_chatbot(capsys):
    import sys

    sys.path.append("example_agents/chatbot")
    from example_agents.chatbot.main import ChatBot
    from example_agents.chatbot.env import MultiChatEnv

    env_generator = MultiChatEnv()
    client_env = env_generator()
    client_env.reset()
    chat_bot = ChatBot(env_generator)
    # Say something in the room for the agent to hear
    response_txt, _, _, _ = client_env.step("one")
    # Agent hears "one" on this advance, but can't respond yet
    chat_bot.advance()
    response_txt, _, _, _ = client_env.step("")
    assert response_txt == "", "chatbot should have no strings in memory"
    # Agent responds with a random selection from memory (which is only "one")
    chat_bot.advance()
    response_txt, _, _, _ = client_env.step("")
    assert response_txt == "one", "chatbot should repeat strings from memory"
    # TODO(andyk): also test CommandLineListener


def run_agent_in_dir(
    agent_dir,
    virtualenv,
    main_file="main.py",
    env_arg="",
    req_file="requirements.txt",
    main_file_args=[],
):
    print(f"Installing {req_file} with cwd {agent_dir}")
    virtualenv.run(
        ["pip", "install", "-r", req_file], cwd=Path(agent_dir), capture=True
    )
    print(f"Using CLI to run agent in {main_file}")
    args = ["agentos", "run", "--max-iters", "2", main_file]
    if env_arg:
        args.append(env_arg)
    virtualenv.run(args, cwd=Path(agent_dir), capture=True)
    print(f"Running {main_file} with cwd {agent_dir}")
    virtualenv.run(
        ["python", main_file] + main_file_args,
        cwd=Path(agent_dir),
        capture=True,
    )


@pytest.mark.skip(reason="TODO: port run_agent to new abstractions")
def test_rl_agents(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "rl_agents"
    run_agent_in_dir(
        agent_dir,
        virtualenv,
        main_file="reinforce_agent.py",
        env_arg="gym.envs.classic_control.CartPoleEnv",
        main_file_args=["5"],
    )
    # TODO: add tests for DQN, RandomTFAgent
    # from example_agents.rl_agents.dqn_agent import DQNAgent
    # from example_agents.rl_agents.random_nn_policy_agent import RandomTFAgent
    # run_agent(DQNAgent, CartPoleEnv, max_iters=10)
    # run_agent(RandomTFAgent, CartPoleEnv, max_iters=10)


@pytest.mark.skip(reason="TODO: port run_agent to new abstractions")
def test_predictive_coding(virtualenv):
    agent_dir = (
        Path(__file__).parent
        / "example_agents"
        / "predictive_coding"
        / "free_energy_tutorial"
    )
    run_agent_in_dir(agent_dir, virtualenv)


@pytest.mark.skip(reason="TODO: port run_agent to new abstractions")
def test_evolutionary_agent(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "evolutionary_agent"
    run_agent_in_dir(
        agent_dir,
        virtualenv,
        main_file="agent.py",
        env_arg="gym.envs.classic_control.CartPoleEnv",
    )
