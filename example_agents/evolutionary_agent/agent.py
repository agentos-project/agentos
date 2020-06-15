import agentos
import gym
import numpy as np
from tensorflow import keras

"""
population of neural nets
till good policy found or max_generations hit:
    score population, one rollout per citizen
    sort population
    keep top_10%
    population = permute(top_10%) * 10 - 1 + top_1 
"""
class EvolutionaryAgent(agentos.Agent):
    def __init__(self, env_class, population_size=2):
        super().__init__(env_class)
        assert isinstance(self.env, gym.envs.classic_control.CartPoleEnv)
        self.population = self.init_models(population_size)
        print("initialized population of models")

    def step(self):
        #self.train()
        obs = self.env.reset()
        ret = 0
        while True:
            action = self.compute_action(obs)
            print(f"agent about to take env action {action.numpy()[0][0]}")
            obs, reward, done, _ = self.env.step(action)
            print(f"agent stepped in env, res: {(obs, reward, done, None)}")
            ret += reward
            if done:
                break
        print("Agent step {self.num_steps} return: {ret}")

    def compute_action(self, obs):
        policy_nn = self.population[-1]  # assume population sorted worst to best.
        return policy_nn(np.array(obs)[np.newaxis])

    def train(self):
        raise NotImplementedError

    def init_models(self, num_models):
        assert isinstance(self.env.observation_space, gym.spaces.Box) and  \
               isinstance(self.env.action_space, gym.spaces.Discrete)
        print(f"setting up Keras NN with input_shape {self.env.observation_space.shape}")
        return [
            keras.Sequential([
                keras.layers.Dense(4, activation='relu', input_shape=self.env.observation_space.shape),
                keras.layers.Dense(8, activation='relu'),
                keras.layers.Dense(1, activation='relu')#self.env.action_space.n)
            ])
            for i in range(num_models)
        ]

