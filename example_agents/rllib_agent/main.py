from agentos import Agent, run_agent
import argparse
import gym
import ray
import ray.rllib.agents.registry as rllib_registry
from ray.tune.registry import register_env as rllib_reg_env


class RLlibAgent(Agent):
    def __init__(self, env_class, algo_name, rllib_config=None):
        """Init a Ray agent with the given env_class and an algorithm name.

        :param algo_name: A string. For valid values of algo_name, see
        https://github.com/ray-project/ray/blob/master/rllib/agents/registry.py
        """
        if isinstance(env_class, str):
            print(f"calling gym.make({env_class})")
            env_class = gym.make(env_class).unwrapped.__class__
        super().__init__(env_class)
        if not ray.is_initialized():
            ray.init()
        trainer_class = rllib_registry._get_agent_class(algo_name)
        print(type(trainer_class))
        def wrapper(conf): return env_class()  # Ray requires env.__init__ take config.
        rllib_reg_env(env_class.__name__, wrapper)
        self.ray_trainer = trainer_class(config=rllib_config, env=env_class.__name__)
        self._last_obs = self.init_obs

    def step(self):
        action = self.ray_trainer.compute_action(self._last_obs)
        self._last_obs, _, done, _ = self.env.step(action)
        return done

    def train(self, num_iterations):
        """Causes Ray to learn"""
        self.ray_agent.train(num_iterations)


def test_rllib_agent():
    from gym.envs.classic_control import CartPoleEnv
    agent = RLlibAgent(CartPoleEnv, "PPO")
    done = agent.step()
    assert not done, "CartPole never finishes after one random step."
    agent.train(1)
    while not done:
        print("stepping agent")
        done = agent.step()
    assert done


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Run an RLlibAgent.")
    parser.add_argument('gym_env_name', metavar='ENV', type=str,
                        help="The name of gym env.")
    parser.add_argument('algorithm', metavar='ALGO', type=str,
                        help="The name of an RLlib algo. For list of algos, "
                             "see https://github.com/ray-project/ray/blob/"
                             "master/rllib/agents/registry.py")
    args = parser.parse_args()
    run_agent(RLlibAgent, args.gym_env_name, algo_name=args.algorithm)

