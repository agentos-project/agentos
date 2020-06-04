def test_random_agent():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv
    agent = RandomAgent(CartPoleEnv)
    done = agent.step()
    assert not done, "CartPole never finishes after one random step."

def test_rllib_agent():
    from agentos.agents import RLlibAgent
    from gym.envs.classic_control import CartPoleEnv
    agent = RLlibAgent(CartPoleEnv, "PPO")
    done = agent.step()
    assert not done, "CartPole never finishes after one random step."
    agent.train(1)
    while not done:
        print("stepping agent")
        done = agent.step()
    assert done

def test_chat_bot():
    from agentos.agents import RLlibAgent
    from gym.envs.classic_control import CartPoleEnv
