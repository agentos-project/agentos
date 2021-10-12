"""Test suite for AgentOS.

See repo README for instructions to run tests.
"""
import pytest
import subprocess
from pathlib import Path
from agentos import run_component


def test_cli(tmpdir):
    subprocess.run(["agentos", "init"], cwd=tmpdir, check=True)
    expected_file_names = [
        "agent.py",
        "environment.py",
        "policy.py",
        "dataset.py",
        "trainer.py",
        "agentos.ini",
    ]
    for expected_file_name in expected_file_names:
        expected_path = Path(tmpdir) / expected_file_name
        assert expected_path.is_file(), f"{expected_file_name} not found"
    subprocess.run(
        ["agentos", "run", "agent", "-Pnum_episodes=10"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "run", "agent", "--entry-point=learn"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "run", "agent", "--entry-point=reset"],
        cwd=tmpdir,
        check=True,
    )

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


@pytest.mark.skip(reason="TODO: port example agents to new abstractions")
def test_random_agent():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv

    environment = CartPoleEnv()
    environment.reset()
    agent = RandomAgent(environment=environment)
    done = agent.advance()
    assert not done, "CartPole never finishes after one random step."
    run_component(agent)


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


def run_component_in_dir(
    dir_name,
    virtualenv,
    component_name,
    entry_points=["evaluate"],
    req_file="requirements.txt",
):
    if req_file:
        print(f"Installing {req_file} with cwd {dir_name}")
        virtualenv.run(
            ["pip", "install", "-r", req_file],
            cd=Path(dir_name),
            capture=True,
        )
    for entry_point in entry_points:
        print(f"Using CLI to run component {component_name}.{entry_point}.")
        args = ["agentos", "run", component_name, "--entry-point", entry_point]
        virtualenv.run(args, cwd=Path(dir_name), capture=True)


@pytest.mark.skip(reason="TODO: fix installing sb3 requirements.")
def test_sb3_agent(virtualenv):
    agent_dir = Path(__file__).parent.parent / "example_agents" / "sb3_agent"
    run_component_in_dir(
        agent_dir, virtualenv, "agent", entry_points=["evaluate", "learn"]
    )


@pytest.mark.skip(reason="TODO: port run_component to new abstractions")
def test_rl_agents(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "rl_agents"
    run_component_in_dir(
        agent_dir,
        virtualenv,
        "ReinforceAgent",
    )
    # TODO: add tests for DQN, RandomTFAgent
    # from example_agents.rl_agents.dqn_agent import DQNAgent
    # from example_agents.rl_agents.random_nn_policy_agent import RandomTFAgent
    # run_component(DQNAgent, CartPoleEnv, max_iters=10)
    # run_component(RandomTFAgent, CartPoleEnv, max_iters=10)


@pytest.mark.skip(reason="TODO: port run_component to new abstractions")
def test_predictive_coding(virtualenv):
    agent_dir = (
        Path(__file__).parent
        / "example_agents"
        / "predictive_coding"
        / "free_energy_tutorial"
    )
    run_component_in_dir(agent_dir, virtualenv, "agent")


@pytest.mark.skip(reason="TODO: port run_component to new abstractions")
def test_evolutionary_agent(virtualenv):
    agent_dir = Path(__file__).parent / "example_agents" / "evolutionary_agent"
    run_component_in_dir(agent_dir, virtualenv, "agent")
