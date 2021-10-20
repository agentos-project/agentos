import pytest
from pathlib import Path
from tests.utils import run_component_in_dir


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
