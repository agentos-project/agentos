"""Pytest tests for agentos.core."""


# TODO: implement basic API for working with long running objects
#       - test "agentos dir init"
#       - test "agentos server start"
def test_agentos_api():
    import agentos
    from agentos.agents import RandomAgent
    import gym

    agentos.server.start()

    # TODO: Decide how this API will work.
    #       Option 1) Separate conceptual mode for server (long running agents)
    #       Option 2) Expose the underlying python AgentManager object managed by
    #                 the server (probably via serialization + REST)
    am = agentos.server.get_agent_manager()  # returns AgentManagerClient(AgentManager)
    assert am.running
    assert am.num_envs == 0
    assert am.num_agents == 0

    am.add_env(gym.make('CartPole-v1'), name="cartpole")
    am.add_agent(RandomAgent(), "cartpole", auto_start=True)
    assert am.num_envs == 1
    assert am.num_agents == 1


def test_agent_manager():
    from agentos import AgentManager
    from agentos.agents import RandomAgent
    import gym

    am = AgentManager()
    cartpole_env = gym.make('CartPole-v1')
    env_id = am.add_env(cartpole_env)
    assert env_id
    random_agent = RandomAgent()
    agent_id = am.add_agent(random_agent, cartpole_env, auto_start=True)
    assert agent_id

    assert am.remove_agent(agent_id) is random_agent
    assert am.remove_env(env_id) is cartpole_env
