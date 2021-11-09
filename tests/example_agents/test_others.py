import pytest
from tests.utils import run_component_in_dir
from tests.utils import RL_AGENTS_DIR
from tests.utils import PREDICTIVE_CODING_AGENT_DIR
from tests.utils import EVOLUTIONARY_AGENT_DIR


@pytest.mark.skip(reason="TODO: port run_component to new abstractions")
def test_rl_agents(virtualenv):
    run_component_in_dir(
        RL_AGENTS_DIR,
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
    run_component_in_dir(PREDICTIVE_CODING_AGENT_DIR, virtualenv, "agent")


@pytest.mark.skip(reason="TODO: port run_component to new abstractions")
def test_evolutionary_agent(virtualenv):
    run_component_in_dir(EVOLUTIONARY_AGENT_DIR, virtualenv, "agent")
