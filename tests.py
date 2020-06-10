def test_random_agent_step():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv
    agent = RandomAgent(CartPoleEnv)
    done = agent.step()
    assert not done, "CartPole never finishes after one random step."


def test_run_random_agent():
    from agentos.agents import RandomAgent
    from agentos import run_agent
    from gym.envs.classic_control import CartPoleEnv
    run_agent(RandomAgent, CartPoleEnv)
