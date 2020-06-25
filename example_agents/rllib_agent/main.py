from agentos import Agent, run_agent
import argparse
import gym
import importlib
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
        self.done = False

    def advance(self):
        if self.done:
            return True
        action = self.ray_trainer.compute_action(self._last_obs)
        self._last_obs, _, self.done, _ = self.env.step(action)
        return self.done

    def train(self, num_iterations):
        """Causes Ray to learn"""
        self.ray_agent.train(num_iterations)


def test_rllib_agent():
    from gym.envs.classic_control import CartPoleEnv
    agent = RLlibAgent(CartPoleEnv, "PPO")
    done = agent.step()
    assert not done, "CartPole should not finish after one random step."
    agent.train(1)
    while not done:
        print("stepping agent")
        done = agent.step()
    assert done


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Run an RLlibAgent.")
    parser.add_argument('env_module', metavar='ENV_MODULE', type=str,
                        help="The python module of env, will be imported. "
                             "Must be on pythonpath. If this is empty string, "
                             "ENV_CLASSNAME is assumed to be a Gym Env id "
                             "instead of a classname (e.g., CartPole-v1)")
    parser.add_argument('env_classname', metavar='ENV_CLASSNAME', type=str,
                        help="The env class for agent to use.")
    parser.add_argument('algorithm', metavar='ALGO', type=str,
                        help="The name of an RLlib algo. For list of algos, "
                             "see https://github.com/ray-project/ray/blob/"
                             "master/rllib/agents/registry.py")
    args = parser.parse_args()
    env = args.env_classname
    if args.env_module:
        module = importlib.import_module(args.env_module)
        env = getattr(module, args.env_classname)
    run_agent(RLlibAgent, env, algo_name=args.algorithm)

